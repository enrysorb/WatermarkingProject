from stegano import lsb
from PIL import Image, ImageEnhance
from io import BytesIO
import numpy as np
from scipy.fft import dct, idct
import pywt
import hashlib
import struct
import os


class AdvancedWatermarking:
    
    def __init__(self):
        self.block_size = 8  
        self.alpha = 0.1
        self.debug = True
        
    def add_error_correction(self, binary_message: str) -> str:
        """Aggiunge ridondanza per correzione errori"""
        redundant_message = ""
        for bit in binary_message:
            redundant_message += bit * 3
        return redundant_message
    
    def correct_errors(self, binary_message: str) -> str:
        """Corregge errori usando voto di maggioranza"""
        corrected_message = ""
        for i in range(0, len(binary_message), 3):
            if i + 2 < len(binary_message):
                bits = binary_message[i:i+3]
                if bits.count('1') >= 2:
                    corrected_message += '1'
                else:
                    corrected_message += '0'
        return corrected_message    
    
    def text_to_binary(self, text: str) -> str:
        return ''.join(format(ord(char), '08b') for char in text)
    
    def binary_to_text(self, binary: str) -> str:
        text = ''
        for i in range(0, len(binary), 8):
            byte = binary[i:i+8]
            if len(byte) == 8:
                try:
                    char_code = int(byte, 2)
                    if 32 <= char_code <= 126:
                        text += chr(char_code)
                except ValueError:
                    continue
        return text
    
    def apply_dct_watermark(self, image_bytes: bytes, hidden_text: str) -> bytes:
        image = Image.open(BytesIO(image_bytes))
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        img_array = np.array(image, dtype=np.float32)
        height, width, channels = img_array.shape
        
        height = (height // self.block_size) * self.block_size
        width = (width // self.block_size) * self.block_size
        img_array = img_array[:height, :width, :]
        
        binary_message = self.text_to_binary(hidden_text)
        message_length = len(binary_message)
        
        if self.debug:
            print(f"DCT Apply - Messaggio: '{hidden_text}' -> {message_length} bit")
        
        length_header = format(message_length, '032b')
        full_message = length_header + binary_message
        
        max_blocks = (height // self.block_size) * (width // self.block_size)
        if len(full_message) > max_blocks:
            if self.debug:
                print(f"Messaggio troppo lungo: {len(full_message)} bit, massimo {max_blocks} blocchi")
            return image_bytes
        for channel in range(3):
            channel_data = img_array[:, :, channel].copy()
            bit_index = 0
            watermark_strength = 80.0  
            
            for i in range(0, height, self.block_size):
                for j in range(0, width, self.block_size):
                    if bit_index >= len(full_message):
                        break
                    
                    block = channel_data[i:i+self.block_size, j:j+self.block_size]
                    dct_block = dct(dct(block.T, norm='ortho').T, norm='ortho')
                    
                    bit_value = int(full_message[bit_index])
                    
                   
                    positions = [(2, 3), (3, 2), (2, 2), (3, 3), (1, 2), (2, 1)]
                    for pos_idx, (row, col) in enumerate(positions):
                        if bit_value == 1:
                            dct_block[row, col] = abs(dct_block[row, col]) + watermark_strength
                        else:
                            dct_block[row, col] = -(abs(dct_block[row, col]) + watermark_strength)
                    
                    watermarked_block = idct(idct(dct_block.T, norm='ortho').T, norm='ortho')
                    channel_data[i:i+self.block_size, j:j+self.block_size] = watermarked_block
                    
                    bit_index += 1
                
                if bit_index >= len(full_message):
                    break
            
            img_array[:, :, channel] = np.clip(channel_data, 0, 255)
        
        watermarked_image = Image.fromarray(img_array.astype(np.uint8))
        
        output_buffer = BytesIO()
        watermarked_image.save(output_buffer, format='PNG')
        return output_buffer.getvalue()
    
    def extract_dct_watermark(self, image_bytes: bytes) -> str:
        image = Image.open(BytesIO(image_bytes))
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        img_array = np.array(image, dtype=np.float32)
        height, width, channels = img_array.shape
        
        height = (height // self.block_size) * self.block_size
        width = (width // self.block_size) * self.block_size
        
       
        channel_results = []
        
        for channel in range(3):
            channel_data = img_array[:height, :width, channel]
            extracted_bits = []
            
            for i in range(0, height, self.block_size):
                for j in range(0, width, self.block_size):
                    block = channel_data[i:i+self.block_size, j:j+self.block_size]
                    dct_block = dct(dct(block.T, norm='ortho').T, norm='ortho')
                    
                   
                    votes = []
                    positions = [(2, 3), (3, 2), (2, 2), (3, 3), (1, 2), (2, 1)]
                    for row, col in positions:
                        if dct_block[row, col] > 0:
                            votes.append(1)
                        else:
                            votes.append(0)
                    
                    
                    bit_value = 1 if sum(votes) > len(votes) // 2 else 0
                    extracted_bits.append(str(bit_value))
            
            channel_results.append(extracted_bits)

        final_bits = []
        min_length = min(len(result) for result in channel_results)
        
        for i in range(min_length):
            votes = [int(channel_results[ch][i]) for ch in range(3)]
            bit_value = 1 if sum(votes) >= 2 else 0
            final_bits.append(str(bit_value))
        
        if len(final_bits) < 32:
            return ""
        
        length_bits = ''.join(final_bits[:32])
        try:
            message_length = int(length_bits, 2)
        except ValueError:
            return ""
        
        if message_length <= 0 or message_length > 1000 or len(final_bits) < 32 + message_length:
            return ""
        
        message_bits = ''.join(final_bits[32:32 + message_length])
        result = self.binary_to_text(message_bits)
        
        return result
    
    def apply_dwt_watermark(self, image_bytes: bytes, hidden_text: str) -> bytes:
        image = Image.open(BytesIO(image_bytes))
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        img_array = np.array(image, dtype=np.float32)
        
        binary_message = self.text_to_binary(hidden_text)
        length_header = format(len(binary_message), '032b')
        full_message = length_header + binary_message
        
        if self.debug:
            print(f"DWT Apply - Messaggio: '{hidden_text}' -> {len(full_message)} bit")
        
        
        for channel in range(3):
            channel_data = img_array[:, :, channel].copy()
            
            coeffs = pywt.dwt2(channel_data, 'db4')
            cA, (cH, cV, cD) = coeffs
            
            embedding_strength = 50.0  
            
            h, w = cH.shape
            watermarked_cH = cH.copy()
            watermarked_cV = cV.copy()
            watermarked_cD = cD.copy()
            
            
            start_h, start_w = h // 3, w // 3
            end_h, end_w = 2 * h // 3, 2 * w // 3
            
            bit_index = 0
            
           
            for coeff_matrix in [watermarked_cH, watermarked_cV, watermarked_cD]:
                for i in range(start_h, end_h):
                    for j in range(start_w, end_w):
                        if bit_index >= len(full_message):
                            break
                        
                        bit_value = int(full_message[bit_index])
                        original_coeff = coeff_matrix[i, j]
                        
                        quantum = embedding_strength
                        
                        
                        if bit_value == 1:
                            coeff_matrix[i, j] = abs(original_coeff) + quantum
                        else:
                            coeff_matrix[i, j] = -(abs(original_coeff) + quantum)
                        
                        bit_index += 1
                    
                    if bit_index >= len(full_message):
                        break
                
                if bit_index >= len(full_message):
                    break
            
            watermarked_coeffs = (cA, (watermarked_cH, watermarked_cV, watermarked_cD))
            watermarked_channel = pywt.idwt2(watermarked_coeffs, 'db4')
            
            if watermarked_channel.shape != channel_data.shape:
                min_h = min(watermarked_channel.shape[0], channel_data.shape[0])
                min_w = min(watermarked_channel.shape[1], channel_data.shape[1])
                watermarked_channel = watermarked_channel[:min_h, :min_w]
                img_array = img_array[:min_h, :min_w, :]
            
            watermarked_channel = np.clip(watermarked_channel, 0, 255)
            img_array[:, :, channel] = watermarked_channel
        
        if self.debug:
            print(f"DWT Apply - Embedded {bit_index} bit")
        
        watermarked_image = Image.fromarray(img_array.astype(np.uint8))
        
        output_buffer = BytesIO()
        watermarked_image.save(output_buffer, format='PNG')
        return output_buffer.getvalue()
    
    def extract_dwt_watermark(self, image_bytes: bytes) -> str:
        image = Image.open(BytesIO(image_bytes))
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        img_array = np.array(image, dtype=np.float32)
        
        channel_results = []
        
        for channel in range(3):
            channel_data = img_array[:, :, channel]
            
            coeffs = pywt.dwt2(channel_data, 'db4')
            cA, (cH, cV, cD) = coeffs
            
            h, w = cH.shape
            start_h, start_w = h // 3, w // 3
            end_h, end_w = 2 * h // 3, 2 * w // 3
            
            extracted_bits = []
            
            for coeff_matrix in [cH, cV, cD]:
                for i in range(start_h, end_h):
                    for j in range(start_w, end_w):
                        if len(extracted_bits) >= 2000:
                            break
                        
                        coeff_value = coeff_matrix[i, j]
                        
                        if coeff_value > 0:
                            extracted_bits.append('1')
                        else:
                            extracted_bits.append('0')
                    
                    if len(extracted_bits) >= 2000:
                        break
                
                if len(extracted_bits) >= 2000:
                    break
            
            channel_results.append(extracted_bits)
        final_bits = []
        min_length = min(len(result) for result in channel_results)
        
        for i in range(min_length):
            votes = [int(channel_results[ch][i]) for ch in range(3)]
            bit_value = 1 if sum(votes) >= 2 else 0
            final_bits.append(str(bit_value))
        
        if self.debug:
            print(f"DWT Extract - Estratti {len(final_bits)} bit")
            print(f"DWT Extract - Prime 42 bit: {''.join(final_bits[:42])}")
        
        if len(final_bits) < 32:
            return ""
        
        length_bits = ''.join(final_bits[:32])
        try:
            message_length = int(length_bits, 2)
            if self.debug:
                print(f"DWT Extract - Lunghezza messaggio: {message_length}")
        except ValueError:
            return ""
        
        if message_length <= 0 or message_length > 1000 or len(final_bits) < 32 + message_length:
            if self.debug:
                print(f"DWT Extract - Lunghezza non valida: {message_length}")
            return ""
        
        message_bits = ''.join(final_bits[32:32 + message_length])
        result = self.binary_to_text(message_bits)
        
        if self.debug:
            print(f"DWT Extract - Bit messaggio: {message_bits}")
            print(f"DWT Extract - Risultato: '{result}'")
        
        return result
    
    def apply_robust_watermark(self, image_bytes: bytes, hidden_text: str) -> bytes:
        return self.apply_dct_watermark(image_bytes, hidden_text)
    
    def extract_robust_watermark(self, image_bytes: bytes) -> str:
        return self.extract_dct_watermark(image_bytes)
    
    def apply_jpeg_compression(self, image_bytes: bytes, quality: int = 85) -> bytes:
        """Applica compressione JPEG con la qualità specificata"""
        image = Image.open(BytesIO(image_bytes))
        
        # Converte in RGB se necessario
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        output_buffer = BytesIO()
        image.save(output_buffer, format='JPEG', quality=quality, optimize=True)
        return output_buffer.getvalue()
    
    def apply_crop(self, image_bytes: bytes, crop_percentage: float = 0.8) -> bytes:
        """
        Croppa l'immagine dal centro mantenendo una percentuale della dimensione originale
        
        Args:
            image_bytes: Bytes dell'immagine
            crop_percentage: Percentuale dell'immagine da mantenere (0.8 = 80%)
        """
        image = Image.open(BytesIO(image_bytes))
        width, height = image.size
        new_width = int(width * crop_percentage)
        new_height = int(height * crop_percentage)
        
        left = (width - new_width) // 2
        top = (height - new_height) // 2
        right = left + new_width
        bottom = top + new_height
        
        cropped_image = image.crop((left, top, right, bottom))
        
        output_buffer = BytesIO()
        cropped_image.save(output_buffer, format='PNG')
        return output_buffer.getvalue()
    
    def apply_brightness_adjustment(self, image_bytes: bytes, brightness_factor: float = 1.2) -> bytes:
        """
        Modifica la luminosità dell'immagine
        
        Args:
            image_bytes: Bytes dell'immagine
            brightness_factor: Fattore di luminosità (1.0 = originale, >1.0 = più luminosa, <1.0 = più scura)
        """
        image = Image.open(BytesIO(image_bytes))
        enhancer = ImageEnhance.Brightness(image)
        brightened_image = enhancer.enhance(brightness_factor)
        
        output_buffer = BytesIO()
        brightened_image.save(output_buffer, format='PNG')
        return output_buffer.getvalue()
    
    def apply_contrast_adjustment(self, image_bytes: bytes, contrast_factor: float = 1.2) -> bytes:
        """
        Modifica il contrasto dell'immagine
        
        Args:
            image_bytes: Bytes dell'immagine
            contrast_factor: Fattore di contrasto (1.0 = originale, >1.0 = più contrasto, <1.0 = meno contrasto)
        """
        image = Image.open(BytesIO(image_bytes))
        enhancer = ImageEnhance.Contrast(image)
        contrast_image = enhancer.enhance(contrast_factor)
        
        output_buffer = BytesIO()
        contrast_image.save(output_buffer, format='PNG')
        return output_buffer.getvalue()
    
    def apply_rotation(self, image_bytes: bytes, angle: float = 5.0) -> bytes:
        """
        Ruota l'immagine di un angolo specificato
        
        Args:
            image_bytes: Bytes dell'immagine
            angle: Angolo di rotazione in gradi
        """
        image = Image.open(BytesIO(image_bytes))
        rotated_image = image.rotate(angle, expand=False, fillcolor='white')
        
        output_buffer = BytesIO()
        rotated_image.save(output_buffer, format='PNG')
        return output_buffer.getvalue()
    
    def apply_scaling(self, image_bytes: bytes, scale_factor: float = 0.8) -> bytes:
        """
        Scala l'immagine e poi la riporta alla dimensione originale
        
        Args:
            image_bytes: Bytes dell'immagine
            scale_factor: Fattore di scala (0.8 = riduce all'80%, poi riporta alla dimensione originale)
        """
        image = Image.open(BytesIO(image_bytes))
        original_size = image.size
        new_width = int(original_size[0] * scale_factor)
        new_height = int(original_size[1] * scale_factor)
        scaled_down = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        scaled_back = scaled_down.resize(original_size, Image.Resampling.LANCZOS)
        
        output_buffer = BytesIO()
        scaled_back.save(output_buffer, format='PNG')
        return output_buffer.getvalue()
    
    def test_crop_robustness(self, image_bytes: bytes, hidden_text: str, method: str = 'dct') -> dict:
        """
        Testa la robustezza del watermark contro il cropping
        """
        results = {}
        crop_percentages = [0.95, 0.9, 0.85, 0.8, 0.75, 0.7, 0.65, 0.6, 0.55, 0.5]
        if method == 'dct':
            watermarked_image = self.apply_dct_watermark(image_bytes, hidden_text)
        elif method == 'dwt':
            watermarked_image = self.apply_dwt_watermark(image_bytes, hidden_text)
        elif method == 'lsb':
            watermarked_image = apply_invisible_watermark_advanced(image_bytes, hidden_text, 'lsb')
        else:
            raise ValueError(f"Metodo non supportato: {method}")
        
        print(f"\n=== TEST ROBUSTEZZA CROP - Metodo: {method.upper()} ===")
        print(f"Testo nascosto: '{hidden_text}'")
        print("-" * 60)
        
        for crop_perc in crop_percentages:
            cropped_image = self.apply_crop(watermarked_image, crop_perc)
            if method == 'dct':
                extracted_text = self.extract_dct_watermark(cropped_image)
            elif method == 'dwt':
                extracted_text = self.extract_dwt_watermark(cropped_image)
            elif method == 'lsb':
                extracted_text = extract_invisible_watermark_advanced(cropped_image, 'lsb')

            accuracy = self.calculate_text_accuracy(hidden_text, extracted_text)
            success = extracted_text == hidden_text
            
            results[crop_perc] = {
                'extracted_text': extracted_text,
                'accuracy': accuracy,
                'success': success,
                'cropped_size': len(cropped_image)
            }
            
            status = "✓ PASS" if success else "✗ FAIL"
            print(f"Crop {crop_perc*100:4.1f}%: {status} | Estratto: '{extracted_text}' | Accuracy: {accuracy:.1f}%")
        
        return results
    
    def test_brightness_robustness(self, image_bytes: bytes, hidden_text: str, method: str = 'dct') -> dict:
        """
        Testa la robustezza del watermark contro le modifiche di luminosità
        """
        results = {}
        brightness_factors = [0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.8, 2.0]
        
        if method == 'dct':
            watermarked_image = self.apply_dct_watermark(image_bytes, hidden_text)
        elif method == 'dwt':
            watermarked_image = self.apply_dwt_watermark(image_bytes, hidden_text)
        elif method == 'lsb':
            watermarked_image = apply_invisible_watermark_advanced(image_bytes, hidden_text, 'lsb')
        else:
            raise ValueError(f"Metodo non supportato: {method}")
        
        print(f"\n=== TEST ROBUSTEZZA LUMINOSITÀ - Metodo: {method.upper()} ===")
        print(f"Testo nascosto: '{hidden_text}'")
        print("-" * 60)
        
        for brightness in brightness_factors:
           
            bright_image = self.apply_brightness_adjustment(watermarked_image, brightness)
            
            if method == 'dct':
                extracted_text = self.extract_dct_watermark(bright_image)
            elif method == 'dwt':
                extracted_text = self.extract_dwt_watermark(bright_image)
            elif method == 'lsb':
                extracted_text = extract_invisible_watermark_advanced(bright_image, 'lsb')
         
            accuracy = self.calculate_text_accuracy(hidden_text, extracted_text)
            success = extracted_text == hidden_text
            
            results[brightness] = {
                'extracted_text': extracted_text,
                'accuracy': accuracy,
                'success': success
            }
            
            status = "✓ PASS" if success else "✗ FAIL"
            brightness_desc = "più scura" if brightness < 1.0 else "più luminosa" if brightness > 1.0 else "originale"
            print(f"Luminosità {brightness:4.1f}x ({brightness_desc:>12}): {status} | Estratto: '{extracted_text}' | Accuracy: {accuracy:.1f}%")
        
        return results
    
    def test_contrast_robustness(self, image_bytes: bytes, hidden_text: str, method: str = 'dct') -> dict:
        """
        Testa la robustezza del watermark contro le modifiche di contrasto
        """
        results = {}
        contrast_factors = [0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.8, 2.0]
        
        if method == 'dct':
            watermarked_image = self.apply_dct_watermark(image_bytes, hidden_text)
        elif method == 'dwt':
            watermarked_image = self.apply_dwt_watermark(image_bytes, hidden_text)
        elif method == 'lsb':
            watermarked_image = apply_invisible_watermark_advanced(image_bytes, hidden_text, 'lsb')
        else:
            raise ValueError(f"Metodo non supportato: {method}")
        
        print(f"\n=== TEST ROBUSTEZZA CONTRASTO - Metodo: {method.upper()} ===")
        print(f"Testo nascosto: '{hidden_text}'")
        print("-" * 60)
        
        for contrast in contrast_factors:
            contrast_image = self.apply_contrast_adjustment(watermarked_image, contrast)
            if method == 'dct':
                extracted_text = self.extract_dct_watermark(contrast_image)
            elif method == 'dwt':
                extracted_text = self.extract_dwt_watermark(contrast_image)
            elif method == 'lsb':
                extracted_text = extract_invisible_watermark_advanced(contrast_image, 'lsb')
            accuracy = self.calculate_text_accuracy(hidden_text, extracted_text)
            success = extracted_text == hidden_text
            
            results[contrast] = {
                'extracted_text': extracted_text,
                'accuracy': accuracy,
                'success': success
            }
            
            status = "PASS" if success else "FAIL"
            contrast_desc = "meno contrasto" if contrast < 1.0 else "più contrasto" if contrast > 1.0 else "originale"
            print(f"Contrasto {contrast:4.1f}x ({contrast_desc:>14}): {status} | Estratto: '{extracted_text}' | Accuracy: {accuracy:.1f}%")
        
        return results
    
    def test_rotation_robustness(self, image_bytes: bytes, hidden_text: str, method: str = 'dct') -> dict:
        """
        Testa la robustezza del watermark contro la rotazione
        """
        results = {}
        rotation_angles = [-10, -5, -3, -1, 0, 1, 3, 5, 10, 15, 20, 30, 45, 90]

        if method == 'dct':
            watermarked_image = self.apply_dct_watermark(image_bytes, hidden_text)
        elif method == 'dwt':
            watermarked_image = self.apply_dwt_watermark(image_bytes, hidden_text)
        elif method == 'lsb':
            watermarked_image = apply_invisible_watermark_advanced(image_bytes, hidden_text, 'lsb')
        else:
            raise ValueError(f"Metodo non supportato: {method}")
        
        print(f"\n=== TEST ROBUSTEZZA ROTAZIONE - Metodo: {method.upper()} ===")
        print(f"Testo nascosto: '{hidden_text}'")
        print("-" * 60)
        
        for angle in rotation_angles:
            rotated_image = self.apply_rotation(watermarked_image, angle)
            if method == 'dct':
                extracted_text = self.extract_dct_watermark(rotated_image)
            elif method == 'dwt':
                extracted_text = self.extract_dwt_watermark(rotated_image)
            elif method == 'lsb':
                extracted_text = extract_invisible_watermark_advanced(rotated_image, 'lsb')
            accuracy = self.calculate_text_accuracy(hidden_text, extracted_text)
            success = extracted_text == hidden_text
            
            results[angle] = {
                'extracted_text': extracted_text,
                'accuracy': accuracy,
                'success': success
            }
            
            status = "✓ PASS" if success else "✗ FAIL"
            print(f"Rotazione {angle:+3d}°: {status} | Estratto: '{extracted_text}' | Accuracy: {accuracy:.1f}%")
        
        return results
    
    def test_scaling_robustness(self, image_bytes: bytes, hidden_text: str, method: str = 'dct') -> dict:
        """
        Testa la robustezza del watermark contro il ridimensionamento
        """
        results = {}
        scale_factors = [0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 1.1, 1.2, 1.3, 1.4, 1.5]
        if method == 'dct':
            watermarked_image = self.apply_dct_watermark(image_bytes, hidden_text)
        elif method == 'dwt':
            watermarked_image = self.apply_dwt_watermark(image_bytes, hidden_text)
        elif method == 'lsb':
            watermarked_image = apply_invisible_watermark_advanced(image_bytes, hidden_text, 'lsb')
        else:
            raise ValueError(f"Metodo non supportato: {method}")
        
        print(f"\n=== TEST ROBUSTEZZA SCALING - Metodo: {method.upper()} ===")
        print(f"Testo nascosto: '{hidden_text}'")
        print("-" * 60)
        
        for scale in scale_factors:
            scaled_image = self.apply_scaling(watermarked_image, scale)
            if method == 'dct':
                extracted_text = self.extract_dct_watermark(scaled_image)
            elif method == 'dwt':
                extracted_text = self.extract_dwt_watermark(scaled_image)
            elif method == 'lsb':
                extracted_text = extract_invisible_watermark_advanced(scaled_image, 'lsb')
            accuracy = self.calculate_text_accuracy(hidden_text, extracted_text)
            success = extracted_text == hidden_text
            
            results[scale] = {
                'extracted_text': extracted_text,
                'accuracy': accuracy,
                'success': success
            }
            
            status = "PASS" if success else "FAIL"
            print(f"Scala {scale:4.1f}x: {status} | Estratto: '{extracted_text}' | Accuracy: {accuracy:.1f}%")
        
        return results
    
    def test_jpeg_robustness(self, image_bytes: bytes, hidden_text: str, method: str = 'dct') -> dict:
        """
        Testa la robustezza del watermark contro compressione JPEG
        con diversi livelli di qualità
        """
        results = {}
        quality_levels = [95, 90, 85, 80]
        if method == 'dct':
            watermarked_image = self.apply_dct_watermark(image_bytes, hidden_text)
        elif method == 'dwt':
            watermarked_image = self.apply_dwt_watermark(image_bytes, hidden_text)
        elif method == 'lsb':
            watermarked_image = apply_invisible_watermark_advanced(image_bytes, hidden_text, 'lsb')
        else:
            raise ValueError(f"Metodo non supportato: {method}")
        
        print(f"\n=== TEST ROBUSTEZZA JPEG - Metodo: {method.upper()} ===")
        print(f"Testo nascosto: '{hidden_text}'")
        print("-" * 60)
        
        for quality in quality_levels:
            compressed_image = self.apply_jpeg_compression(watermarked_image, quality)
            if method == 'dct':
                extracted_text = self.extract_dct_watermark(compressed_image)
            elif method == 'dwt':
                extracted_text = self.extract_dwt_watermark(compressed_image)
            elif method == 'lsb':
                extracted_text = extract_invisible_watermark_advanced(compressed_image, 'lsb')
            accuracy = self.calculate_text_accuracy(hidden_text, extracted_text)
            success = extracted_text == hidden_text
            
            results[quality] = {
                'extracted_text': extracted_text,
                'accuracy': accuracy,
                'success': success,
                'compressed_size': len(compressed_image)
            }
            
            status = "✓ PASS" if success else "✗ FAIL"
            print(f"Qualità {quality:2d}%: {status} | Estratto: '{extracted_text}' | Accuracy: {accuracy:.1f}% | Size: {len(compressed_image):,} bytes")
        
        return results
    
    def calculate_text_accuracy(self, original: str, extracted: str) -> float:
        """Calcola l'accuratezza tra testo originale e estratto"""
        if not original or not extracted:
            return 0.0
        
        correct_chars = sum(1 for i, char in enumerate(extracted) 
                          if i < len(original) and char == original[i])
        
        return (correct_chars / len(original)) * 100
    
    def run_comprehensive_robustness_test(self, image_bytes: bytes, test_texts: list = None) -> dict:
        """
        Esegue un test completo di robustezza per tutti i metodi e tutti i tipi di attacco
        """
        if test_texts is None:
            test_texts = ["Test per il waterarking"]
        
        methods = ['dct', 'dwt', 'lsb']
        all_results = {}
        
        print("=" * 80)
        print("TEST COMPLETO DI ROBUSTEZZA WATERMARK")
        print("=" * 80)
        
        for method in methods:
            method_results = {}
            
            for text in test_texts:
                text_results = {}
                
                try:
                 
                    text_results['jpeg'] = self.test_jpeg_robustness(image_bytes, text, method)
                
                    text_results['crop'] = self.test_crop_robustness(image_bytes, text, method)
                    
                    text_results['brightness'] = self.test_brightness_robustness(image_bytes, text, method)
                    
                    text_results['contrast'] = self.test_contrast_robustness(image_bytes, text, method)
                    
                    text_results['rotation'] = self.test_rotation_robustness(image_bytes, text, method)
                   
                    text_results['scaling'] = self.test_scaling_robustness(image_bytes, text, method)
                    
                except Exception as e:
                    print(f"Errore con metodo {method} e testo '{text}': {e}")
                    text_results = {}
                
                method_results[text] = text_results
            
            all_results[method] = method_results
        
        self.generate_comprehensive_summary_report(all_results)
        
        return all_results
    
    def generate_comprehensive_summary_report(self, results: dict):
        """Genera un report riassuntivo completo dei risultati"""
        print("\n" + "=" * 80)
        print("REPORT RIASSUNTIVO COMPLETO")
        print("=" * 80)
        
        attack_types = ['jpeg', 'crop', 'brightness', 'contrast', 'rotation', 'scaling']
        
        for method in results.keys():
            print(f"\n{method.upper()} - Robustezza per tipo di attacco:")
            print("-" * 50)
            
            for attack_type in attack_types:
                attack_success = {}
                total_tests = 0
                total_successes = 0
                
                for text, text_results in results[method].items():
                    if attack_type in text_results:
                        for param, result in text_results[attack_type].items():
                            total_tests += 1
                            if result['success']:
                                total_successes += 1
                
                if total_tests > 0:
                    percentage = (total_successes / total_tests) * 100
                    print(f"  {attack_type.capitalize():12}: {total_successes:3d}/{total_tests:3d} successi ({percentage:5.1f}%)")
                else:
                    print(f"  {attack_type.capitalize():12}: Nessun test disponibile")
        
        print(f"\n{'='*50}")
        print("CLASSIFICA ROBUSTEZZA GENERALE")
        print(f"{'='*50}")
        
        method_scores = {}
        for method in results.keys():
            total_tests = 0
            total_successes = 0
            
            for text, text_results in results[method].items():
                for attack_type in attack_types:
                    if attack_type in text_results:
                        for param, result in text_results[attack_type].items():
                            total_tests += 1
                            if result['success']:
                                total_successes += 1
            
            if total_tests > 0:
                method_scores[method] = (total_successes / total_tests) * 100
            else:
                method_scores[method] = 0
        
        sorted_methods = sorted(method_scores.items(), key=lambda x: x[1], reverse=True)
        
        for i, (method, score) in enumerate(sorted_methods, 1):
            print(f"{i}. {method.upper()}: {score:.1f}% successi complessivi")


def apply_invisible_watermark_advanced(image_bytes: bytes, hidden_text: str, method: str = 'dct') -> bytes:
    if method == 'lsb':
        from stegano import lsb
        input_image = Image.open(BytesIO(image_bytes))
        output_path = BytesIO()
        secret = lsb.hide(input_image, hidden_text)
        secret.save(output_path, format="PNG")
        return output_path.getvalue()
    
    watermarker = AdvancedWatermarking()
    
    if method == 'dct':
        return watermarker.apply_dct_watermark(image_bytes, hidden_text)
    elif method == 'dwt':
        return watermarker.apply_dwt_watermark(image_bytes, hidden_text)
    elif method == 'robust':
        return watermarker.apply_robust_watermark(image_bytes, hidden_text)
    else:
        raise ValueError(f"Metodo non supportato: {method}")


def extract_invisible_watermark_advanced(image_bytes: bytes, method: str = 'dct') -> str:
    if method == 'lsb':
        from stegano import lsb
        input_image = Image.open(BytesIO(image_bytes))
        try:
            result = lsb.reveal(input_image)
            return result if result else ""
        except:
            return ""
    
    watermarker = AdvancedWatermarking()
    
    if method == 'dct':
        return watermarker.extract_dct_watermark(image_bytes)
    elif method == 'dwt':
        return watermarker.extract_dwt_watermark(image_bytes)
    elif method == 'robust':
        return watermarker.extract_robust_watermark(image_bytes)
    else:
        return ""
