from typing import Optional

class OcrScheduler:
    def __init__(self):
        self.running_page: Optional[str] = None
        self.pending_page: Optional[str] = None

    def request_ocr(self, page_path: str) -> bool:
        """
        Request OCR for a page.
        Returns True if the page should start OCR immediately, False otherwise.
        """
        if self.running_page == page_path:
            # Already running for this page
            return False
            
        if self.running_page is None:
            # Nothing is running, start immediately
            self.running_page = page_path
            return True
            
        # Something else is running, store as pending
        self.pending_page = page_path
        return False

    def on_ocr_complete(self, completed_page: str, current_page: str, page_needs_ocr: bool) -> Optional[str]:
        """
        Notify that OCR has completed for a page.
        Returns the path of the next page to start OCR for, or None if nothing to start.
        """
        if self.running_page == completed_page:
            self.running_page = None
            
        # Always check what the current page is
        if current_page and page_needs_ocr:
            self.pending_page = None
            # DO NOT set running_page here! Let start_ocr call request_ocr to set it.
            return current_page
            
        # If current page doesn't need OCR, we just stay idle
        self.pending_page = None
        return None
