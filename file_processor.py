import os
import re
import pandas as pd
from PyPDF2 import PdfReader
from docx import Document
import uuid
import logging
from typing import List, Dict, Any

class DocumentProcessor:
    """Core document processing engine for NeuroLM"""
    
    def __init__(self):
        self.chunk_size = 1500  # Optimal for embeddings
        self.overlap = 150      # Maintain context continuity
        self.min_chunk_length = 50  # Minimum viable chunk size
        
    def process_file(self, file, user_id: str) -> List[str]:
        """Main processing pipeline with enhanced error handling"""
        try:
            # Validate file
            self._validate_file(file)
            
            # Temporary file handling
            file_ext = os.path.splitext(file.name)[1].lower()
            temp_path = f"tmp_{user_id}_{uuid.uuid4()}{file_ext}"
            
            with open(temp_path, "wb") as f:
                f.write(file.getbuffer())
            
            # Extract content
            content = self._extract_content(temp_path, file_ext)
            
            # Cleanup temporary file
            if os.path.exists(temp_path):
                os.remove(temp_path)
            
            # Check for valid extraction
            if not content or len(content.strip()) < self.min_chunk_length:
                raise ValueError("Insufficient text extracted from document")
            
            # Create knowledge chunks
            chunks = self._create_chunks(content)
            
            return chunks
        
        except Exception as e:
            # Cleanup on error
            if 'temp_path' in locals() and os.path.exists(temp_path):
                os.remove(temp_path)
            logging.error(f"Processing failed for {file.name}: {str(e)}")
            raise
    
    def _validate_file(self, file) -> None:
        """Basic file validation"""
        if not file:
            raise ValueError("No file provided")
        
        if file.size == 0:
            raise ValueError("File is empty")
        
        if file.size > 10 * 1024 * 1024:  # 10MB limit
            raise ValueError("File too large (max 10MB)")
        
        allowed_extensions = {'.pdf', '.docx', '.csv', '.txt', '.md', '.xlsx', '.xls'}
        file_ext = os.path.splitext(file.name)[1].lower()
        
        if file_ext not in allowed_extensions:
            raise ValueError(f"Unsupported file type: {file_ext}")
    
    def _extract_content(self, file_path: str, file_ext: str) -> str:
        """Enhanced extraction with format-specific methods"""
        try:
            if file_ext == '.pdf':
                return self._extract_pdf(file_path)
            elif file_ext == '.docx':
                return self._extract_docx(file_path)
            elif file_ext in ['.xlsx', '.xls']:
                return self._extract_excel(file_path)
            elif file_ext == '.csv':
                return self._extract_csv(file_path)
            elif file_ext in ['.txt', '.md']:
                return self._extract_text(file_path)
            else:
                raise ValueError(f"Unsupported file extension: {file_ext}")
        except Exception as e:
            raise ValueError(f"Failed to extract content: {str(e)}")
    
    def _extract_pdf(self, path: str) -> str:
        """Extract text from PDF files"""
        try:
            text = ""
            reader = PdfReader(path)
            
            for page_num, page in enumerate(reader.pages):
                page_text = page.extract_text()
                if page_text and page_text.strip():
                    text += f"\n--- Page {page_num + 1} ---\n"
                    text += page_text + "\n"
            
            if not text.strip():
                raise ValueError("No text found in PDF - may be image-based")
            
            return text.strip()
        
        except Exception as e:
            raise ValueError(f"PDF extraction failed: {str(e)}")
    
    def _extract_docx(self, path: str) -> str:
        """Extract text from Word documents"""
        try:
            doc = Document(path)
            paragraphs = []
            
            for para in doc.paragraphs:
                if para.text.strip():
                    paragraphs.append(para.text.strip())
            
            text = "\n\n".join(paragraphs)
            
            if not text.strip():
                raise ValueError("No text found in Word document")
            
            return text
        
        except Exception as e:
            raise ValueError(f"Word document extraction failed: {str(e)}")
    
    def _extract_excel(self, path: str) -> str:
        """Extract data from Excel files"""
        try:
            xl_file = pd.ExcelFile(path)
            all_content = []
            
            for sheet_name in xl_file.sheet_names:
                df = pd.read_excel(xl_file, sheet_name=sheet_name)
                
                if not df.empty:
                    all_content.append(f"=== Sheet: {sheet_name} ===")
                    all_content.append(df.to_string(index=False, max_rows=1000))
                    all_content.append("")
            
            content = "\n".join(all_content)
            
            if not content.strip():
                raise ValueError("No data found in Excel file")
            
            return content
        
        except Exception as e:
            raise ValueError(f"Excel extraction failed: {str(e)}")
    
    def _extract_csv(self, path: str) -> str:
        """Extract data from CSV files"""
        try:
            df = pd.read_csv(path)
            
            if df.empty:
                raise ValueError("CSV file is empty")
            
            return df.to_string(index=False, max_rows=1000)
        
        except Exception as e:
            raise ValueError(f"CSV extraction failed: {str(e)}")
    
    def _extract_text(self, path: str) -> str:
        """Extract content from text files"""
        try:
            # Try different encodings
            encodings = ['utf-8', 'utf-16', 'latin-1', 'cp1252']
            
            for encoding in encodings:
                try:
                    with open(path, 'r', encoding=encoding) as f:
                        content = f.read()
                    if content.strip():
                        return content
                except UnicodeDecodeError:
                    continue
            
            raise ValueError("Could not decode text file with any supported encoding")
        
        except Exception as e:
            raise ValueError(f"Text extraction failed: {str(e)}")
    
    def _create_chunks(self, text: str) -> List[str]:
        """Semantically-aware chunking with overlap"""
        if not text or len(text.strip()) < self.min_chunk_length:
            return []
        
        # Clean the text
        text = self._clean_text(text)
        
        # Split into sentences for better chunking
        sentences = self._split_into_sentences(text)
        
        chunks = []
        current_chunk = ""
        
        for sentence in sentences:
            # Check if adding this sentence would exceed chunk size
            if len(current_chunk) + len(sentence) + 1 <= self.chunk_size:
                current_chunk += sentence + " "
            else:
                # Save current chunk if it's long enough
                if len(current_chunk.strip()) >= self.min_chunk_length:
                    chunks.append(current_chunk.strip())
                
                # Start new chunk with overlap from previous chunk
                if current_chunk:
                    overlap_start = max(0, len(current_chunk) - self.overlap)
                    overlap_text = current_chunk[overlap_start:].strip()
                    current_chunk = overlap_text + " " + sentence + " "
                else:
                    current_chunk = sentence + " "
        
        # Add the final chunk
        if len(current_chunk.strip()) >= self.min_chunk_length:
            chunks.append(current_chunk.strip())
        
        return chunks
    
    def _clean_text(self, text: str) -> str:
        """Clean and normalize text"""
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove excessive newlines but preserve paragraph breaks
        text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)
        
        # Remove special characters that might interfere with processing
        text = re.sub(r'[^\w\s\-.,;:!?()[\]{}"\'/\n]', ' ', text)
        
        return text.strip()
    
    def _split_into_sentences(self, text: str) -> List[str]:
        """Split text into sentences for better chunking"""
        # Simple sentence splitting - can be enhanced with NLTK if needed
        sentences = re.split(r'(?<=[.!?])\s+', text)
        
        # Filter out very short sentences
        sentences = [s.strip() for s in sentences if len(s.strip()) > 10]
        
        return sentences
    
    def get_file_info(self, file) -> Dict[str, Any]:
        """Get metadata about uploaded file"""
        return {
            "name": file.name,
            "size": file.size,
            "type": file.type,
            "extension": os.path.splitext(file.name)[1].lower()
        }