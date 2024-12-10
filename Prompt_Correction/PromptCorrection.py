import re
from typing import Dict, List

class PromptCorrectionAgent:
    def __init__(self):
        # Common misspellings dictionary (you can expand this)
        self.common_misspellings = {
            'functtions': 'functions',
            'u': 'you',
            'ur': 'your',
            'doesnt': "doesn't",
            'dont': "don't",
            'cant': "can't",
            # Add more common misspellings
        }
        
        # Common prompt patterns to check
        self.prompt_patterns = [
            r'\b(please|kindly|can you)\b',
            r'\b(generate|create|make|write)\b',
            r'\b(using|with|in)\b',
        ]

    def correct_spelling(self, text: str) -> str:
        """
        Corrects common spelling mistakes using the misspellings dictionary.
        """
        words = text.split()
        corrected_words = [self.common_misspellings.get(word.lower(), word) for word in words]
        return ' '.join(corrected_words)

    def fix_capitalization(self, text: str) -> str:
        """
        Fixes capitalization issues in the text.
        """
        # Capitalize first letter of the sentence
        if text:
            text = text[0].upper() + text[1:] if len(text) > 1 else text.upper()
            
        # Capitalize common terms that should always be capitalized
        common_caps = ['python', 'javascript', 'html', 'css', 'sql']
        for word in common_caps:
            text = re.sub(rf'\b{word}\b', word.upper(), text, flags=re.IGNORECASE)
            
        return text

    def fix_punctuation(self, text: str) -> str:
        """
        Fixes punctuation issues in the text.
        """
        # Add space after punctuation if missing
        for punct in ['.', ',', '!', '?', ';', ':']:
            text = text.replace(f'{punct}', f'{punct} ')
            text = text.replace(f'{punct}  ', f'{punct} ')
        
        # Remove space before punctuation
        text = re.sub(r'\s+([.,!?;:])', r'\1', text)
        
        # Ensure sentence ends with punctuation
        if not text.rstrip()[-1] in ['.', '!', '?']:
            text = text.rstrip() + '.'
            
        return text

    def fix_spacing(self, text: str) -> str:
        """
        Fixes spacing issues in the text.
        """
        # Remove multiple spaces
        text = ' '.join(text.split())
        
        # Add space after punctuation if missing
        text = re.sub(r'([.,!?;:])(\w)', r'\1 \2', text)
        
        return text.strip()

    def enhance_prompt_structure(self, text: str) -> str:
        """
        Enhances the prompt structure by adding missing elements.
        """
        text = text.strip()
        
        # Add polite request if missing
        has_polite = any(re.search(pattern, text.lower()) for pattern in self.prompt_patterns)
        if not has_polite:
            text = "Please " + text
            
        # Add context marker if missing (like "using Python" or "in Python")
        if not any(word in text.lower() for word in ['using', 'in', 'with']):
            if any(lang in text.lower() for lang in ['python', 'javascript', 'java']):
                text = text.rstrip('.') + ' using the specified language.'
                
        return text

    def correct_prompt(self, text: str) -> Dict[str, str]:
        """
        Main function that applies all corrections and returns both corrected text
        and correction details.
        """
        original = text
        corrections = {}
        
        # Apply corrections step by step
        text = self.correct_spelling(text)
        if text != original:
            corrections['spelling'] = 'Fixed spelling mistakes'
            
        text = self.fix_spacing(text)
        if text != original:
            corrections['spacing'] = 'Fixed spacing issues'
            
        text = self.fix_capitalization(text)
        if text != original:
            corrections['capitalization'] = 'Fixed capitalization'
            
        text = self.fix_punctuation(text)
        if text != original:
            corrections['punctuation'] = 'Fixed punctuation'
            
        text = self.enhance_prompt_structure(text)
        if text != original:
            corrections['structure'] = 'Enhanced prompt structure'
            
        return {
            'original': original,
            'corrected': text,
            'corrections_made': corrections
        }

# Example usage
def demonstrate_correction_agent():
    agent = PromptCorrectionAgent()
    test_prompts = [
        "write python code for calculator",
        "GENERATE a function in python",
        "make    me  a  website",
        "create databse query",
        "can u help me fix this codei wrote"
    ]
    
    for prompt in test_prompts:
        result = agent.correct_prompt(prompt)
        print("\nOriginal:", result['original'])
        print("Corrected:", result['corrected'])
        print("Corrections made:", result['corrections_made'])

if __name__ == "__main__":
    demonstrate_correction_agent()