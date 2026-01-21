import os
import pkg_resources
from symspellpy import SymSpell, Verbosity

class SpellChecker:
    def __init__(self, dictionary_path=None, max_edit_distance=2):
        self.sym_spell = SymSpell(max_dictionary_edit_distance=max_edit_distance, prefix_length=7)
        self.max_edit_distance = max_edit_distance
        
        # Load dictionary
        if dictionary_path and os.path.exists(dictionary_path):
            print(f"Loading dictionary from {dictionary_path}...")
            # term_index=0, count_index=1, separator=" "
            if not self.sym_spell.load_dictionary(dictionary_path, term_index=0, count_index=1, separator=" ", encoding="utf-8"):
                print("Dictionary file not found")
        else:
            # Fallback to default frequency dictionary if available (or empty)
            print("No custom dictionary found. Using default frequency dictionary from symspellpy if available.")
            dictionary_path = pkg_resources.resource_filename(
                "symspellpy", "frequency_dictionary_en_82_765.txt")
            if not self.sym_spell.load_dictionary(dictionary_path, term_index=0, count_index=1):
                print("Default dictionary not found")
                
    def check_word(self, word):
        """
        Check if a word is valid (in dictionary).
        Returns True/False.
        """
        # lookup returns list of SuggestItem. If word is in dict, edit_distance=0 should be found.
        # But for simple existence check, we can check if it's in sym_spell.words
        return word.lower() in self.sym_spell.words

    def suggest(self, word):
        """
        Get suggestions for a misspelled word.
        Returns list of (term, distance, count).
        """
        suggestions = self.sym_spell.lookup(word, Verbosity.CLOSEST, max_edit_distance=self.max_edit_distance)
        return [(s.term, s.distance, s.count) for s in suggestions]

    def lookup_compound(self, text):
        """
        Compound lookup for multi-word strings (not used primarily here but good to have).
        """
        suggestions = self.sym_spell.lookup_compound(text, max_edit_distance=self.max_edit_distance)
        return [(s.term, s.distance, s.count) for s in suggestions]
