import json
import os
import sys
import time
import multiprocessing
from concurrent.futures import ProcessPoolExecutor
import nltk
from nltk.stem import WordNetLemmatizer
from nltk.corpus import wordnet

# Add project root to path to import hardware
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import hardware

try:
    from backend.spell_checker import SpellChecker
except ImportError:
    from spell_checker import SpellChecker

# Global variables for worker processes (Lightweight)
worker_lemmatizer = None
worker_whitelist = None

def get_wordnet_pos(treebank_tag):
    if treebank_tag.startswith('J'):
        return wordnet.ADJ
    elif treebank_tag.startswith('V'):
        return wordnet.VERB
    elif treebank_tag.startswith('N'):
        return wordnet.NOUN
    elif treebank_tag.startswith('R'):
        return wordnet.ADV
    else:
        return wordnet.NOUN # Default to noun

def init_worker(whitelist_path):
    """Initialize lightweight resources for each worker process (No Dictionary)."""
    global worker_lemmatizer, worker_whitelist
    
    # Load Whitelist
    worker_whitelist = set()
    if os.path.exists(whitelist_path):
        try:
            with open(whitelist_path, 'r', encoding='utf-8') as f:
                for line in f:
                    w = line.strip()
                    if w:
                        worker_whitelist.add(w)
                        worker_whitelist.add(w.lower())
        except Exception as e:
            print(f"Worker failed to load whitelist: {e}")
    
    # Initialize Lemmatizer only (Small memory footprint)
    try:
        worker_lemmatizer = WordNetLemmatizer()
    except Exception as e:
        print(f"Worker failed to load lemmatizer: {e}")

def analyze_article_nlp(article):
    """
    Perform NLP analysis on an article.
    Extracts potential candidates for spell checking.
    Does NOT load the full dictionary.
    """
    global worker_lemmatizer, worker_whitelist
    
    text = article.get("content", "")
    if not text:
        return None
        
    candidates = []
    
    try:
        # Tokenize into sentences
        sentences = nltk.sent_tokenize(text)
        
        for sentence in sentences:
            # Tokenize words
            tokens = nltk.word_tokenize(sentence)
            # POS Tagging
            tagged = nltk.pos_tag(tokens)
            # Named Entity Recognition
            chunked = nltk.ne_chunk(tagged)
            
            for chunk in chunked:
                if hasattr(chunk, 'label'):
                    # It's a Named Entity (e.g., PERSON, GPE, ORGANIZATION)
                    continue
                else:
                    # It's a regular token (word, tag) tuple
                    word, tag = chunk
                    
                    # Filter: Alpha only, length > 3
                    if not word.isalpha() or len(word) <= 3:
                        continue
                        
                    # Skip common stopwords
                    if word.lower() in {"this", "that", "with", "from", "have", "what", "when", "where", "which", "your", "their", "there"}:
                        continue
                    
                    # Skip Proper Nouns (NNP, NNPS)
                    if tag in ('NNP', 'NNPS'):
                        continue

                    # Whitelist Check
                    if word in worker_whitelist or word.lower() in worker_whitelist:
                        continue

                    # Generate Variants for Validation (moved from SpellChecker logic)
                    variants = set()
                    variants.add(word)
                    
                    # Lemmatization
                    wn_pos = get_wordnet_pos(tag)
                    lemma = worker_lemmatizer.lemmatize(word.lower(), pos=wn_pos)
                    variants.add(lemma)
                    variants.add(lemma.lower())
                    
                    # Fallback Lemmatization (Multi-POS)
                    if wn_pos == wordnet.NOUN:
                        # Try as Verb
                        lemma_v = worker_lemmatizer.lemmatize(word.lower(), pos=wordnet.VERB)
                        variants.add(lemma_v)
                    elif wn_pos == wordnet.VERB:
                        # Try as Noun
                        lemma_n = worker_lemmatizer.lemmatize(word.lower(), pos=wordnet.NOUN)
                        variants.add(lemma_n)
                    elif wn_pos == wordnet.ADJ:
                        # Try as Verb
                        lemma_v = worker_lemmatizer.lemmatize(word.lower(), pos=wordnet.VERB)
                        variants.add(lemma_v)
                    
                    # Add candidate
                    candidates.append({
                        "word": word,
                        "context": sentence.strip()[:100] + "...",
                        "tag": tag,
                        "lemma": lemma,
                        "variants": list(variants)
                    })
                            
        return {
            "title": article.get("title"),
            "country": article.get("country"),
            "date": article.get("date"),
            "scraped_at": article.get("scraped_at"),
            "candidates": candidates
        }
            
    except Exception as e:
        print(f"Error processing article '{article.get('title', 'unknown')}': {e}")
        return None

class SpellDetectionPipeline:
    def __init__(self):
        self.input_file = os.path.join("data", "sample_news_scraped.json")
        self.dict_path = os.path.join("data", "symspell_freq_dict.txt")
        self.output_file = os.path.join("data", "detected_errors.json")
        self.whitelist_path = os.path.join("data", "whitelist.txt")
        self.gpu_info = hardware.get_gpu_diagnostics()
        self.checker = None # Loaded in run()
        
    def ensure_nltk(self):
        try:
            nltk.data.find('tokenizers/punkt')
            nltk.data.find('taggers/averaged_perceptron_tagger')
            nltk.data.find('chunkers/maxent_ne_chunker')
            nltk.data.find('corpora/words')
            nltk.data.find('corpora/wordnet')
        except LookupError:
            print("Downloading NLTK data...")
            nltk.download('punkt')
            nltk.download('averaged_perceptron_tagger')
            nltk.download('maxent_ne_chunker')
            nltk.download('words')
            nltk.download('wordnet')

    def run(self):
        print("\n" + "="*50)
        print("   SpellAtlas Detection Pipeline - Memory Optimized")
        print("="*50)
        
        # 1. Hardware Diagnostics
        print("\n[Hardware Diagnostics]")
        print(hardware.format_gpu_diagnostics(self.gpu_info))
        
        # 2. Resource Check
        print("\n[Resource Check]")
        self.ensure_nltk()
        
        if not os.path.exists(self.input_file):
            print(f"Error: Input file {self.input_file} not found.")
            return

        # 3. Load Data
        print("\n[Data Loading]")
        with open(self.input_file, 'r', encoding='utf-8') as f:
            articles = json.load(f)
        print(f"Loaded {len(articles)} articles.")

        # 4. Initialize Single SpellChecker (Shared Memory by Architecture)
        print("\n[Memory Optimization]")
        print("Initializing Master SpellChecker (Single Instance)...")
        # This instance is ONLY in the main process. Workers do not duplicate it.
        # This achieves 'Shared Memory' efficiency without complex IPC.
        try:
            self.checker = SpellChecker(dictionary_path=self.dict_path)
            print("Master Dictionary Loaded Successfully.")
        except Exception as e:
            print(f"Failed to load dictionary: {e}")
            return

        # 5. Parallel Processing (Map-Reduce Style)
        # Workers: NLP Analysis (CPU bound) -> Output Candidates
        # Main: Spell Check (Memory bound) -> Output Errors
        
        num_workers = os.cpu_count()
        if num_workers is None:
            num_workers = 4
            
        print(f"\n[Execution Strategy]")
        if self.gpu_info.get("torch_cuda"):
            print("Status: GPU Acceleration Available (Future Integration)")
        else:
            print("Status: CPU Optimization Active")
        print(f"Method: Decoupled Parallel NLP + Centralized Dictionary (Pool Size: {num_workers})")
        
        start_time = time.time()
        
        all_errors = []
        print(f"Processing started...")
        
        # Use ProcessPoolExecutor for NLP
        with ProcessPoolExecutor(max_workers=num_workers, initializer=init_worker, initargs=(self.whitelist_path,)) as executor:
            # Stream results to keep memory low
            results_iterator = executor.map(analyze_article_nlp, articles)
            
            for result in results_iterator:
                if not result:
                    continue
                
                article_errors = []
                candidates = result.get("candidates", [])
                
                # Verify candidates against the Master Dictionary
                for cand in candidates:
                    word = cand["word"]
                    variants = cand["variants"]
                    
                    # Check if any variant is valid
                    is_valid = False
                    for v in variants:
                        if self.checker.check_word(v):
                            is_valid = True
                            break
                    
                    if not is_valid:
                        # Confirm Error & Generate Suggestions
                        suggestions = self.checker.suggest(word)
                        if suggestions:
                            top_sugg = suggestions[0]
                            if top_sugg[0].lower() != word.lower():
                                article_errors.append({
                                    "word": word,
                                    "context": cand["context"],
                                    "suggestion": top_sugg[0],
                                    "distance": top_sugg[1],
                                    "tag": cand["tag"],
                                    "lemma": cand["lemma"]
                                })
                
                if article_errors:
                    # Deduplicate
                    unique_errors = {f"{e['word']}->{e['suggestion']}": e for e in article_errors}.values()
                    all_errors.append({
                        "title": result["title"],
                        "country": result["country"],
                        "date": result.get("date"),
                        "scraped_at": result.get("scraped_at"),
                        "errors": list(unique_errors)
                    })
                    
        elapsed = time.time() - start_time
        print(f"\n[Results]")
        print(f"Processed {len(articles)} articles in {elapsed:.2f}s")
        print(f"Found errors in {len(all_errors)} articles.")
        
        # 6. Save Results
        with open(self.output_file, 'w', encoding='utf-8') as f:
            json.dump(all_errors, f, indent=2, ensure_ascii=False)
        print(f"Saved error report to {self.output_file}")
        
        # Sample
        if all_errors:
            sample = all_errors[0]
            print(f"\nSample from '{sample['title']}':")
            for err in sample['errors'][:5]:
                print(f"  - {err['word']} ({err['tag']}) -> {err['suggestion']} (dist={err['distance']})")

if __name__ == "__main__":
    # Windows support for multiprocessing
    multiprocessing.freeze_support()
    pipeline = SpellDetectionPipeline()
    pipeline.run()
