import random
import time
from datetime import datetime
from data import DATA

class Simulator:
    # Core logic to generate a single news item
    @staticmethod
    def generate_item():
        country = Simulator.get_random(DATA["COUNTRIES"])
        headline_base = Simulator.generate_headline()
        has_error = random.random() < 0.3 # 30% error rate

        final_headline = headline_base
        error_detail = None

        if has_error:
            words = headline_base.split(' ')
            if len(words) > 0:
                idx = random.randint(0, len(words) - 1)
                original_word = words[idx]
                typos = Simulator.introduce_typo(original_word)
                
                # If typo actually changed the word
                if typos != original_word:
                    words[idx] = typos
                    final_headline = ' '.join(words)
                    error_detail = {
                        "error_word": typos,
                        "corrected_word": original_word
                    }

        return {
            "id": f"{int(time.time() * 1000)}{random.randint(1000, 9999)}",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "country_name": country["name"],
            "country_code": country["code"],
            "coordinates": { "lat": country["lat"], "lng": country["lng"] },
            "headline": final_headline,
            "has_error": bool(error_detail),
            "error_detail": error_detail
        }

    @staticmethod
    def generate_headline():
        s = Simulator.get_random(DATA["HEADLINES"]["SUBJECTS"])
        v = Simulator.get_random(DATA["HEADLINES"]["VERBS"])
        o = Simulator.get_random(DATA["HEADLINES"]["OBJECTS"])
        return f"{s} {v} {o}"

    @staticmethod
    def introduce_typo(word):
        if len(word) < 3:
            return word
        
        type_val = random.random()
        chars = list(word)
        idx = random.randint(0, len(chars) - 1)

        # 1. Swap (33%)
        if type_val < 0.33 and idx < len(chars) - 1:
            chars[idx], chars[idx+1] = chars[idx+1], chars[idx]
        # 2. Drop (33%)
        elif type_val < 0.66:
            chars.pop(idx)
        # 3. Adjacency (33%)
        else:
            char = chars[idx].lower()
            adj = DATA["KEYBOARD_ADJACENCY"].get(char)
            if adj:
                replacement = random.choice(list(adj))
                if chars[idx].isupper():
                    replacement = replacement.upper()
                chars[idx] = replacement
        
        return "".join(chars)

    @staticmethod
    def get_random(arr):
        return random.choice(arr)
