import cv2
import numpy as np
from PIL import Image
import io
import logging
import os
import glob
from typing import Tuple, Dict

logger = logging.getLogger(__name__)

class ImageAnalyzer:
    def __init__(self):
        self.screenshot_indicators = [
            "telegram",
            "screenshot", 
            "report",
            "admin"
        ]
        
        # Trusted educational keywords - if image has these, be more lenient
        self.educational_keywords = [
            "neet", "jee", "physics", "chemistry", "biology", "mathematics", 
            "question", "answer", "solution", "ncert", "cbse", "study",
            "exam", "preparation", "practice", "test", "mock", "sample"
        ]
        
        # Load competitor logo templates
        self.logo_templates = {}
        self._load_competitor_logos()
    
    def _load_competitor_logos(self):
        """Load all competitor logo templates from logos folder"""
        logo_folder = os.path.join(os.path.dirname(__file__), 'logos')
        
        if not os.path.exists(logo_folder):
            logger.warning(f"Logos folder not found: {logo_folder}")
            return
        
        # Load all image files from logos folder
        logo_files = glob.glob(os.path.join(logo_folder, '*'))
        logo_extensions = ['.png', '.jpg', '.jpeg', '.bmp', '.tiff']
        
        for logo_file in logo_files:
            if any(logo_file.lower().endswith(ext) for ext in logo_extensions):
                try:
                    # Load logo template
                    template = cv2.imread(logo_file, cv2.IMREAD_COLOR)
                    if template is not None:
                        logo_name = os.path.splitext(os.path.basename(logo_file))[0]
                        self.logo_templates[logo_name] = template
                        logger.info(f"Loaded logo template: {logo_name}")
                    else:
                        logger.warning(f"Failed to load logo: {logo_file}")
                except Exception as e:
                    logger.error(f"Error loading logo {logo_file}: {e}")
        
        logger.info(f"Loaded {len(self.logo_templates)} competitor logo templates")
    
    def analyze_image(self, image_data: bytes, caption: str = "") -> Dict[str, any]:
        try:
            image = Image.open(io.BytesIO(image_data))
            
            # Check if this appears to be educational content
            is_educational = self._is_educational_content(caption)
            
            # If no caption provided, assume it's educational (doubt/question image)
            # This is common in NEET channels where students share question images without text
            if not caption.strip():
                is_educational = True
                logger.info("No caption provided - assuming educational content")
            
            # If educational, be very lenient - only block obvious competitor logos
            if is_educational:
                has_competitor_logo = self._detect_competitor_logos_strict(image)
            else:
                # For non-educational images, use normal detection
                has_competitor_logo = self._detect_competitor_logos(image)
            
            return {
                "is_safe": not has_competitor_logo,
                "has_competitor_logo": has_competitor_logo,
                "is_educational": is_educational,
                "width": image.width,
                "height": image.height,
                "reason": "competitor_logo" if has_competitor_logo else "safe"
            }
        except Exception as e:
            logger.error(f"Error analyzing image: {e}")
            return {
                "is_safe": False,
                "error": str(e)
            }
    
    def _detect_screenshot(self, image: Image.Image) -> bool:
        width, height = image.size
        aspect_ratio = width / height
        
        common_screenshot_ratios = [
            (16, 9), (18, 9), (4, 3), (3, 2), (16, 10)
        ]
        
        for w, h in common_screenshot_ratios:
            expected_ratio = w / h
            if abs(aspect_ratio - expected_ratio) < 0.1:
                if width >= 300 and height >= 300:
                    return True
        
        return False
    
    def _detect_suspicious_content(self, image: Image.Image) -> bool:
        try:
            img_array = np.array(image.convert('RGB'))
            gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
            
            edges = cv2.Canny(gray, 50, 150)
            edge_density = np.sum(edges > 0) / (gray.shape[0] * gray.shape[1])
            
            if edge_density > 0.15:
                return True
            
            hist = cv2.calcHist([gray], [0], None, [256], [0, 256])
            hist_normalized = hist / np.sum(hist)
            entropy = -np.sum(hist_normalized * np.log2(hist_normalized + 1e-10))
            
            if entropy < 4.0:
                return True
            
            return False
        except Exception as e:
            logger.error(f"Error in suspicious content detection: {e}")
            return False
    
    def _detect_competitor_logos(self, image: Image.Image) -> bool:
        """Detect competitor logos using template matching"""
        try:
            # Convert PIL image to OpenCV format
            img_array = np.array(image.convert('RGB'))
            img_bgr = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
            img_gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
            
            # Check against all loaded logo templates
            for logo_name, template in self.logo_templates.items():
                if self._match_template(img_gray, template, logo_name):
                    logger.info(f"Detected competitor logo: {logo_name}")
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error in competitor logo detection: {e}")
            return False
    
    def _match_template(self, image_gray, template, logo_name: str) -> bool:
        """Match a single template against the image using multiple scales"""
        try:
            template_gray = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)
            template_h, template_w = template_gray.shape
            
            # If template is larger than image, skip
            if template_h > image_gray.shape[0] or template_w > image_gray.shape[1]:
                return False
            
            # Try multiple scales to catch logos of different sizes
            scales = [0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 1.1, 1.2]
            
            for scale in scales:
                # Resize template
                new_w = int(template_w * scale)
                new_h = int(template_h * scale)
                
                # Skip if resized template is too large
                if new_h > image_gray.shape[0] or new_w > image_gray.shape[1]:
                    continue
                
                resized_template = cv2.resize(template_gray, (new_w, new_h))
                
                # Perform template matching
                result = cv2.matchTemplate(image_gray, resized_template, cv2.TM_CCOEFF_NORMED)
                _, max_val, _, _ = cv2.minMaxLoc(result)
                
                # Threshold for logo detection (adjusted to reduce false positives)
                threshold = 0.8  # 80% similarity to reduce false positives with educational content
                
                if max_val >= threshold:
                    logger.info(f"Logo {logo_name} detected with confidence: {max_val:.2f} at scale: {scale}")
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error in template matching for {logo_name}: {e}")
            return False
    
    def _is_educational_content(self, caption: str) -> bool:
        """Check if image appears to be educational content"""
        if not caption:
            return False
        
        caption_lower = caption.lower()
        return any(keyword in caption_lower for keyword in self.educational_keywords)
    
    def _detect_competitor_logos_strict(self, image: Image.Image) -> bool:
        """Strict competitor logo detection for educational content - only flag obvious matches"""
        try:
            # Convert PIL image to OpenCV format
            img_array = np.array(image.convert('RGB'))
            img_bgr = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
            img_gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
            
            # Check against all loaded logo templates with stricter threshold
            for logo_name, template in self.logo_templates.items():
                if self._match_template_strict(img_gray, template, logo_name):
                    logger.info(f"Detected competitor logo (strict): {logo_name}")
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error in strict competitor logo detection: {e}")
            return False
    
    def _match_template_strict(self, image_gray, template, logo_name: str) -> bool:
        """Strict template matching for educational content - higher threshold"""
        try:
            template_gray = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)
            template_h, template_w = template_gray.shape
            
            # If template is larger than image, skip
            if template_h > image_gray.shape[0] or template_w > image_gray.shape[1]:
                return False
            
            # Try fewer scales for stricter matching
            scales = [0.8, 0.9, 1.0, 1.1, 1.2]
            
            for scale in scales:
                # Resize template
                new_w = int(template_w * scale)
                new_h = int(template_h * scale)
                
                # Skip if resized template is too large
                if new_h > image_gray.shape[0] or new_w > image_gray.shape[1]:
                    continue
                
                resized_template = cv2.resize(template_gray, (new_w, new_h))
                
                # Perform template matching
                result = cv2.matchTemplate(image_gray, resized_template, cv2.TM_CCOEFF_NORMED)
                _, max_val, _, _ = cv2.minMaxLoc(result)
                
                # Very strict threshold for educational content
                threshold = 0.9  # 90% similarity - only flag obvious competitor logos
                
                if max_val >= threshold:
                    logger.info(f"Logo {logo_name} detected (strict) with confidence: {max_val:.2f} at scale: {scale}")
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error in strict template matching for {logo_name}: {e}")
            return False