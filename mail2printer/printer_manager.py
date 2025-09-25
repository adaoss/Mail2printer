import tempfile
import mimetypes
from pathlib import Path
from PIL import Image  # <-- add this import at the top with others

class PrinterManager:
    # ... (other methods) ...

    def print_file(self, file_path: Path, title: str = None) -> bool:
        """
        Print a file
        
        Args:
            file_path: Path to file to print
            title: Job title (defaults to filename)
            
        Returns:
            True if print job submitted successfully
        """
        if not file_path.exists():
            logger.error(f"File not found: {file_path}")
            return False
        
        title = title or file_path.name
        content_type, _ = mimetypes.guess_type(str(file_path))
        
        # NEW: If file is an image, convert to PDF first!
        if content_type and content_type.startswith("image/"):
            logger.info(f"Converting image to PDF before printing: {file_path}")
            pdf_path = self._image_to_pdf(file_path)
            if pdf_path:
                result = self._print_file(pdf_path, title, "application/pdf")
                try:
                    os.unlink(pdf_path)
                except Exception:
                    pass
                return result
            else:
                logger.error(f"Failed to convert image {file_path} to PDF.")
                return False

        return self._print_file(str(file_path), title, content_type)

    def _image_to_pdf(self, image_path: Path) -> str or None:
        """
        Converts an image file to a PDF and returns the path to the PDF.
        """
        try:
            with Image.open(image_path) as img:
                # Convert mode if necessary for PDF
                if img.mode in ("RGBA", "P"):
                    img = img.convert("RGB")
                with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp_pdf:
                    img.save(tmp_pdf, "PDF", resolution=100.0)
                    logger.debug(f"Image converted to PDF: {tmp_pdf.name}")
                    return tmp_pdf.name
        except Exception as e:
            logger.error(f"Error converting image to PDF: {e}")
            return None
