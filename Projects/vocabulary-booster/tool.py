import json
import re

def parse_dictionary_text(text_content: str) -> list:
    """
    Phân tích cú pháp văn bản từ điển theo định dạng tùy chỉnh
    và chuyển đổi nó thành cấu trúc dữ liệu Python (list of dicts).
    """
    dictionary_data = []
    current_word_entry = None
    current_meaning_entry = None
    current_definition_entry = None
    is_current_entry_idiom = False # Flag to track if the current entry is an idiom

    # Biểu thức chính quy để khớp các mẫu dòng
    # Cập nhật để khớp cả @ và !
    # LƯU Ý: Phần 'word' (?P<word>[^/]+?) giả định rằng từ tiếng Anh không chứa dấu '/'
    # nếu có phiên âm đi kèm. Dấu '/' được coi là dấu phân cách bắt đầu phiên âm.
    entry_start_pattern = re.compile(r"^(?P<prefix>[!@])(?P<word>[^/]+?)\s*(?P<pronunciation>/.*?)?$")
    
    # Danh sách các loại từ tiếng Việt phổ biến để phân biệt với phần ghi chú
    # Thêm các loại từ phổ biến khác nếu cần
    part_of_speech_list = [
        "danh từ", "tính từ", "phó từ", "mạo từ", "giới từ", "động từ",
        "liên từ", "thán từ", "đại từ", "số từ", "lượng từ", "chỉ từ", "trạng từ"
    ]
    # Tạo regex an toàn từ danh sách các loại từ
    part_of_speech_regex_str = "|".join(map(re.escape, part_of_speech_list))
    # Cập nhật để chỉ khớp loại từ cụ thể, phần còn lại là ghi chú
    part_of_speech_pattern = re.compile(r"^\*\s*(" + part_of_speech_regex_str + r")\s*(.*)?$") # Group 1: POS, Group 2: rest of line (notes)
    
    definition_pattern = re.compile(r"^- (.+)$") # - definition
    example_pattern = re.compile(r"^=([^+\n]+)\+(.+)$") # = english_example+vietnamese_translation

    lines = text_content.strip().split('\n')

    for line_num, line in enumerate(lines):
        line = line.strip()
        if not line:
            continue # Bỏ qua dòng trống

        # 1. Dòng bắt đầu từ mới (@ hoặc !)
        match_entry_start = entry_start_pattern.match(line)
        if match_entry_start:
            # Lưu từ trước đó nếu có
            if current_word_entry:
                if current_meaning_entry:
                    if current_definition_entry:
                        current_meaning_entry['definitions'].append(current_definition_entry)
                    current_word_entry['meanings'].append(current_meaning_entry)
                dictionary_data.append(current_word_entry)

            word = match_entry_start.group('word').strip()
            pronunciation = match_entry_start.group('pronunciation').strip() if match_entry_start.group('pronunciation') else None
            is_current_entry_idiom = (match_entry_start.group('prefix') == '!')

            current_word_entry = {
                "word": word,
                "pronunciation": pronunciation,
                "meanings": []
            }
            current_meaning_entry = None
            current_definition_entry = None
            continue

        # Đảm bảo đã có từ hiện tại trước khi xử lý các dòng khác
        if not current_word_entry:
            print(f"Cảnh báo: Dòng {line_num+1} '{line}' không bắt đầu bằng '@' hoặc '!' nhưng chưa có từ nào được định nghĩa. Bỏ qua.")
            continue

        # 2. Dòng loại từ (*)
        match_pos = part_of_speech_pattern.match(line)
        if match_pos:
            # Lưu nghĩa trước đó nếu có
            if current_meaning_entry:
                if current_definition_entry:
                    current_meaning_entry['definitions'].append(current_definition_entry)
                current_word_entry['meanings'].append(current_meaning_entry)

            part_of_speech = match_pos.group(1).strip()
            # Phần còn lại của dòng sau loại từ là ghi chú
            raw_notes = match_pos.group(2).strip() if match_pos.group(2) else None
            
            # Nếu raw_notes bắt đầu bằng dấu phẩy, loại bỏ nó
            if raw_notes and raw_notes.startswith(','):
                notes = raw_notes[1:].strip()
            else:
                notes = raw_notes

            current_meaning_entry = {
                "part_of_speech": part_of_speech,
                "notes": notes if notes else None, # Gán None nếu chuỗi rỗng
                "definitions": []
            }
            current_definition_entry = None
            is_current_entry_idiom = False # Reset idiom flag if a POS is found
            continue

        # 3. Dòng định nghĩa (-)
        match_def = definition_pattern.match(line)
        if match_def:
            # Nếu là một mục idiom và chưa có meaning entry, tạo một cái mặc định
            if is_current_entry_idiom and not current_meaning_entry:
                current_meaning_entry = {
                    "part_of_speech": "idiom", # Hoặc "phrase", tùy bạn muốn định nghĩa
                    "notes": None,
                    "definitions": []
                }
                current_word_entry['meanings'].append(current_meaning_entry)

            # Lưu định nghĩa trước đó nếu có
            if current_definition_entry and current_meaning_entry:
                current_meaning_entry['definitions'].append(current_definition_entry)

            definition_text = match_def.group(1).strip()
            current_definition_entry = {
                "text": definition_text,
                "examples": []
            }
            continue

        # 4. Dòng ví dụ (=)
        match_example = example_pattern.match(line)
        if match_example:
            if current_definition_entry:
                english_example = match_example.group(1).strip()
                vietnamese_translation = match_example.group(2).strip()
                current_definition_entry['examples'].append({
                    "english": english_example,
                    "vietnamese": vietnamese_translation
                })
            else:
                print(f"Cảnh báo: Dòng {line_num+1} '{line}' là ví dụ nhưng chưa có định nghĩa nào được định nghĩa. Bỏ qua.")
            continue

        # Nếu dòng không khớp với bất kỳ mẫu nào
        print(f"Cảnh báo: Dòng {line_num+1} '{line}' không khớp với bất kỳ mẫu nào. Bỏ qua.")

    # Lưu từ cuối cùng sau khi vòng lặp kết thúc
    if current_word_entry:
        if current_meaning_entry:
            if current_definition_entry:
                current_meaning_entry['definitions'].append(current_definition_entry)
            current_word_entry['meanings'].append(current_meaning_entry)
        dictionary_data.append(current_word_entry)

    return dictionary_data

def save_to_json_file(data: list, output_filepath: str):
    """Lưu dữ liệu từ điển đã phân tích cú pháp vào một file JSON."""
    try:
        with open(output_filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"Dữ liệu từ điển đã được lưu thành công vào '{output_filepath}'")
    except IOError as e:
        print(f"Lỗi: Không thể ghi file '{output_filepath}': {e}")
    except Exception as e:
        print(f"Lỗi không xác định khi lưu file JSON: {e}")

if __name__ == "__main__":
    # Dữ liệu từ điển mẫu của bạn
    dictionary_text_data = open("english-vietnamese.txt", "r", encoding="utf-8").read()
    output_json_file = "dictionary.json"

    print("Bắt đầu phân tích cú pháp từ điển...")
    parsed_data = parse_dictionary_text(dictionary_text_data)

    if parsed_data:
        print(f"Đã phân tích cú pháp thành công {len(parsed_data)} từ.")
        save_to_json_file(parsed_data, output_json_file)
    else:
        print("Không có dữ liệu nào được phân tích cú pháp.")

    print("\n--- Hoàn thành ---")
