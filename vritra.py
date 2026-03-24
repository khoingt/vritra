import csv
import random
import os
from dotenv import load_dotenv
import google.generativeai as genai
import argparse
 
load_dotenv()
 
# Load Gemini config from .env
_GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
_GEMINI_PROMPT = os.getenv("GEMINI_PROMPT")
 
if _GEMINI_API_KEY:
    genai.configure(api_key=_GEMINI_API_KEY)
    _gemini_model = genai.GenerativeModel("gemini-2.0-flash")
else:
    _gemini_model = None

def generate_weighted_responses():
    """
    Generates a single set of weighted random survey responses.
    Weights are assigned as lists corresponding to the options.
    """
    # Questions and Options taken directly from the sources [1-5]
    # Weights are estimated examples and NOT from the source text.
    
    # Câu 1: Tần suất chơi bóng [1]
    q1_options = ["Có, tôi chơi thường xuyên (ít nhất 1 lần mỗi tuần)", "Thỉnh thoảng (1 đến 3 lần mỗi tháng)", "Hiếm khi hoặc không bao giờ"]
    q1_weights =  [60, 30, 10]

    # Câu 2: Loại giày thường mang [1, 2]
    q2_options = ["Chỉ mang giày thể thao thông thường (sneakers)", "Chỉ mang giày đá bóng (giày đinh/turf)", "Mang cả hai loại", "Tùy thuộc vào tình huống"]
    q2_weights = [20, 25, 35, 20]

    # Câu 3: Quên mang giày đá bóng [2]
    q3_options = ["Có, điều này xảy ra khá thường xuyên", "Có, nhưng chỉ thỉnh thoảng", "Hiếm khi", "Chưa bao giờ"]
    q3_weights = [15, 40, 30, 15]

    # Câu 4: Hành vi khi không có giày đá bóng [2]
    q4_options = ["Vẫn chơi bình thường bằng giày thể thao thông thường", "Mượn giày của người khác", "Không tham gia chơi và chờ lần khác", "Khác"]
    q4_weights = [50, 20, 20, 5]

    # Câu 5: Lý do (Multiple Choice) [3]
    # For multiple choice, we weight the chance of EACH option being selected independently
    q5_options = [
        ("Không muốn bỏ lỡ buổi chơi cùng bạn bè", 0.8), # 80% chance to pick this
        ("Không có lựa chọn nào khác vào lúc đó", 0.6),
        ("Không nghĩ rằng loại giày có ảnh hưởng lớn đến việc chơi", 0.3),
        ("Khác", 0.1)
    ]

    # Câu 6: Nhận thức về độ bám [3]
    q6_options = ["Có, rõ rệt", "Có, nhưng không đáng kể", "Không có sự khác biệt", "Tôi chưa để ý đến điều này"]
    q6_weights = [40, 35, 15, 10]

    # Câu 7: Lo ngại về nguy cơ chấn thương [4]
    q7_options = ["Có, tôi lo ngại khá nhiều", "Có, nhưng tôi vẫn chấp nhận rủi ro đó", "Không lo ngại vì tôi đã quen", "Chưa bao giờ nghĩ đến điều này"]
    q7_weights = [30, 40, 20, 10]

    # Câu 8: Vấn đề cần giải pháp [4]
    q8_options = ["Có, đây là một vấn đề thực sự cần được giải quyết", "Có thể, nhưng không quá cấp bách", "Không, tôi không coi đây là vấn đề lớn"]
    q8_weights = [40, 40, 20]

    # Câu 9: Mức độ quan tâm giải pháp [5]
    q9_options = ["Có, tôi rất quan tâm", "Có thể, tùy thuộc vào giải pháp đó là gì", "Không quan tâm"]
    q9_weights = [45, 40, 15]

    # Selection Logic
    response = {
        "Câu 1": random.choices(q1_options, weights=q1_weights),
        "Câu 2": random.choices(q2_options, weights=q2_weights),
        "Câu 3": random.choices(q3_options, weights=q3_weights),
        "Câu 4": random.choices(q4_options, weights=q4_weights),
        "Câu 6": random.choices(q6_options, weights=q6_weights),
        "Câu 7": random.choices(q7_options, weights=q7_weights),
        "Câu 8": random.choices(q8_options, weights=q8_weights),
        "Câu 9": random.choices(q9_options, weights=q9_weights),
    }

    # Special handling for Question 5 (Checkbox/Multiple Choice) [3]
    selected_q5 = [opt for opt, weight in q5_options if random.random() < weight]
    response["Câu 5"] = "; ".join(selected_q5) if selected_q5 else "N/A"

    # Câu 10: Weighted boolean (70% True / 30% False)
    # If True, generate a Gemini response using the prompt from .env
    q10_true = random.choices([True, False], weights=[70, 30])[0]
    if q10_true and _gemini_model and _GEMINI_PROMPT:
        gemini_response = _gemini_model.generate_content(_GEMINI_PROMPT)
        response["Câu 10"] = gemini_response.text.strip()
    else:
        response["Câu 10"] = ""

    return response

def save_weighted_csv(filename="data.csv", num_records=20):
    fieldnames = ["Câu 1", "Câu 2", "Câu 3", "Câu 4", "Câu 5", "Câu 6", "Câu 7", "Câu 8", "Câu 9", "Câu 10"]
    
    with open(filename, mode='w', newline='', encoding='utf-8-sig') as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        for _ in range(num_records):
            writer.writerow(generate_weighted_responses())
    
    print(f"Generated {num_records} weighted responses in '{filename}'.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate weighted survey responses.")
    parser.add_argument("--records", type=int, default=20, help="Number of records to generate (default: 20)")
    parser.add_argument("--output", type=str, default="data.csv", help="Output CSV filename (default: data.csv)")
    args = parser.parse_args()
 
    save_weighted_csv(filename=args.output, num_records=args.records)