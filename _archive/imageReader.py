from PIL import Image
import cv2
import pytesseract


def parseMyImage (path, tyPath = 'C:\\Program Files\\Tesseract-OCR\\tesseract.exe'):
        image = cv2.imread(path)

        # Preprocessing (optional but recommended)
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        gray = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)[1]

        # Save the preprocessed image (optional)
        cv2.imwrite('preprocessed_image.jpg', gray)

        pytesseract.pytesseract.tesseract_cmd = tyPath
        text = pytesseract.image_to_string(Image.open('preprocessed_image.jpg'))
        
        return text

##print(parseMyImage(path =  'A:\\Code\\Python\\DmSim\\actors\\statReader\\Sample images\\demoTest.jpg'))