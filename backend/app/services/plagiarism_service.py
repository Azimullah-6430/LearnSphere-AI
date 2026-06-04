import hashlib
import difflib
from fuzzywuzzy import fuzz
from app.services.ocr_service import extract_text_from_pdf, extract_text_from_image
import os

class PlagiarismDetectionService:
    """Advanced plagiarism detection service"""
    
    def __init__(self):
        self.similarity_threshold = 0.85
    
    def compare_documents(self, file_path_1, file_path_2):
        """
        Compare two documents for plagiarism
        
        Args:
            file_path_1: Path to first file
            file_path_2: Path to second file
        
        Returns:
            Similarity score (0-1)
        """
        try:
            # Extract text from both files
            text_1 = self._extract_text(file_path_1)
            text_2 = self._extract_text(file_path_2)
            
            if not text_1 or not text_2:
                return 0.0
            
            # Preprocess texts
            text_1 = self._preprocess_text(text_1)
            text_2 = self._preprocess_text(text_2)
            
            # Calculate similarity using multiple methods
            similarity_1 = self._sequence_matcher_similarity(text_1, text_2)
            similarity_2 = self._fuzzy_string_matching(text_1, text_2)
            similarity_3 = self._cosine_similarity(text_1, text_2)
            
            # Average the scores
            avg_similarity = (similarity_1 + similarity_2 + similarity_3) / 3
            
            return min(avg_similarity, 1.0)
        
        except Exception as e:
            return 0.0
    
    def check_file_hash_match(self, file_path_1, file_path_2):
        """
        Check if two files have same content (renamed PDFs)
        
        Args:
            file_path_1: Path to first file
            file_path_2: Path to second file
        
        Returns:
            True if files have same content, False otherwise
        """
        try:
            hash_1 = self._calculate_file_hash(file_path_1)
            hash_2 = self._calculate_file_hash(file_path_2)
            
            return hash_1 == hash_2
        
        except Exception as e:
            return False
    
    def _extract_text(self, file_path):
        """Extract text from file"""
        try:
            if file_path.lower().endswith('.pdf'):
                return extract_text_from_pdf(file_path)
            else:
                return extract_text_from_image(file_path)
        except:
            return ""
    
    def _preprocess_text(self, text):
        """Preprocess text for comparison"""
        # Convert to lowercase
        text = text.lower()
        
        # Remove extra whitespace
        text = ' '.join(text.split())
        
        # Remove special characters but keep alphanumeric and spaces
        import re
        text = re.sub(r'[^a-z0-9\s]', '', text)
        
        return text
    
    def _sequence_matcher_similarity(self, text_1, text_2):
        """Calculate similarity using SequenceMatcher"""
        matcher = difflib.SequenceMatcher(None, text_1, text_2)
        return matcher.ratio()
    
    def _fuzzy_string_matching(self, text_1, text_2):
        """Calculate similarity using fuzzy matching"""
        # Split into words and compare
        words_1 = text_1.split()
        words_2 = text_2.split()
        
        # Use token set ratio for better matching
        return fuzz.token_set_ratio(text_1, text_2) / 100.0
    
    def _cosine_similarity(self, text_1, text_2):
        """Calculate cosine similarity"""
        try:
            from sklearn.feature_extraction.text import TfidfVectorizer
            from sklearn.metrics.pairwise import cosine_similarity
            
            vectorizer = TfidfVectorizer(analyzer='char', ngram_range=(2, 3))
            vectors = vectorizer.fit_transform([text_1, text_2])
            similarity = cosine_similarity(vectors[0], vectors[1])[0][0]
            
            return similarity
        except:
            return 0.5
    
    def _calculate_file_hash(self, file_path):
        """Calculate file hash"""
        sha256_hash = hashlib.sha256()
        
        with open(file_path, 'rb') as f:
            for byte_block in iter(lambda: f.read(4096), b''):
                sha256_hash.update(byte_block)
        
        return sha256_hash.hexdigest()
