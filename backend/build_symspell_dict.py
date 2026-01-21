import csv
import os
from wordfreq import top_n_list, word_frequency

def build_symspell_dictionary():
    """
    Convert OEWN CSV vocabulary to SymSpell dictionary format (term count).
    SymSpell expects: term count
    We use frequency_decimal * 10^9 as the count.
    
    Also supplements with top 10,000 common English words from wordfreq 
    to ensure function words (prepositions, pronouns, etc.) are included,
    as OEWN often lacks them.
    """
    input_csv = os.path.join("data", "oewn_vocab_with_freq.csv")
    output_txt = os.path.join("data", "symspell_freq_dict.txt")
    
    lemma_counts = {}
    
    # 1. Load from OEWN CSV
    if os.path.exists(input_csv):
        print(f"Loading OEWN vocabulary from {input_csv}...")
        
        def process_row(row):
            try:
                lemma = row['lemma'].strip()
                # Skip terms with spaces (multi-word expressions)
                if ' ' in lemma:
                    return
                
                freq_decimal = float(row['frequency_decimal'])
                count = int(freq_decimal * 1_000_000_000)
                if count < 1: 
                    count = 1 
                
                if lemma in lemma_counts:
                    if count > lemma_counts[lemma]:
                        lemma_counts[lemma] = count
                else:
                    lemma_counts[lemma] = count
            except ValueError:
                pass

        try:
            with open(input_csv, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    process_row(row)
        except UnicodeDecodeError:
            print("UTF-8 decode error. Trying with errors='replace'...")
            with open(input_csv, 'r', encoding='utf-8', errors='replace') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    process_row(row)
    else:
        print(f"Warning: {input_csv} not found. Skipping OEWN load.")

    # 2. Supplement with top 30,000 words from wordfreq (English)
    print("Supplementing with top 30,000 words from wordfreq...")
    common_words = top_n_list('en', 30000)
    
    added_count = 0
    for word in common_words:
        if ' ' in word:
            continue
            
        if word not in lemma_counts:
            # Get frequency
            freq = word_frequency(word, 'en')
            count = int(freq * 1_000_000_000)
            if count < 1:
                count = 1
            lemma_counts[word] = count
            added_count += 1
            
    print(f"Added {added_count} common words that were missing in OEWN.")

    # 3. Write to file
    print(f"Writing {len(lemma_counts)} entries to {output_txt}...")
    with open(output_txt, 'w', encoding='utf-8') as f:
        for lemma, count in lemma_counts.items():
            f.write(f"{lemma} {count}\n")
            
    print("Done.")

if __name__ == "__main__":
    build_symspell_dictionary()
