import csv
import random
import argparse
import time
import requests  # You may need to run: pip install requests

# Replace with your actual Google Form ID
FORM_ID = "1FAIpQLSeKZp7pIwRf-O9Sw3y7Tl6_q-jaKRLlWmq49yjykPiCcSzrOA"
FORM_URL = f"https://docs.google.com/forms/d/e/{FORM_ID}/formResponse"

def generate_weighted_responses():
    # Options and Weights [cite: 3, 4, 6]
    q1_options = ["Có, tôi chơi thường xuyên (ít nhất 1 lần mỗi tuần)", "Thỉnh thoảng (1 đến 3 lần mỗi tháng)", "Hiếm khi hoặc không bao giờ"]
    q1_weights = [85.5, 10.5, 4.0]

    q2_options = ["Có, điều này thường xuyên gây khó chịu cho tôi", "Có, nhưng tôi không coi đó là vấn đề lớn", "Không, tôi không cảm thấy bất tiện"]
    q2_weights = [70.2, 20.4, 9.4]

    q3_options = ["Có, tôi vẫn chơi dù biết có thể bị trơn trượt", "Có, nhưng tôi chơi cẩn thận hơn bình thường", "Không, tôi chờ đến khi có giày phù hợp mới chơi"]
    q3_weights = [15.3, 65.2, 19.5]

    q4_options = ["Rất quan tâm, tôi muốn thử ngay", "Quan tâm, nhưng tôi cần biết thêm thông tin", "Không chắc chắn", "Không quan tâm"]
    q4_weights = [28.4, 52.1, 10.5, 9.0]

    q5_choices = [
        ("Phụ kiện có thể bị tuột hoặc lỏng trong khi chơi", 0.45),
        ("Độ bám vẫn không đủ tốt so với giày đá bóng thật", 0.22),
        ("Khó gắn hoặc tháo trong thực tế", 0.14),
        ("Trông không đẹp hoặc kỳ lạ khi đeo", 0.08),
        ("Giá thành quá cao", 0.06),
        ("Không có lo ngại gì đặc biệt", 0.05)
    ]

    q6_options = ["Có, tôi hoàn toàn tin tưởng", "Có thể, nhưng tôi cần dùng thử trước", "Không chắc chắn", "Không, tôi vẫn không tin tưởng dù được đảm bảo chắc chắn"]
    q6_weights = [22.8, 48.2, 20.5, 8.5]

    q7_options = ["Tiện lợi hơn nhiều so với mang thêm giày", "Tiện lợi hơn một chút", "Không có sự khác biệt đáng kể", "Kém tiện lợi hơn so với mang thêm giày"]
    q7_weights = [35.4, 45.3, 10.2, 9.1]

    q8_options = ["Dưới 100.000 VND", "Từ 100.000 đến 200.000 VND", "Từ 200.000 đến 400.000 VND", "Trên 400.000 VND", "Tôi sẽ không mua dù ở mức giá nào"]
    q8_weights = [52.7, 30.1, 10.2, 4.0, 3.0]
    
    q9_options = ["Có, tôi sẽ mua ngay", "Có thể, tôi sẽ cân nhắc thêm", "Không, tôi sẽ không mua"]
    q9_weights = [45, 40, 15]

    # Generate Multiple Choice for Q5 [cite: 6, 11]
    selected_q5 = [opt for opt, weight in q5_choices if random.random() < weight]
    
    response = {
        "entry.793130714": random.choices(q1_options, weights=q1_weights)[0],
        "entry.1605854701": random.choices(q2_options, weights=q2_weights)[0],
        "entry.1887328251": random.choices(q3_options, weights=q3_weights)[0],
        "entry.660043415": random.choices(q4_options, weights=q4_weights)[0],
        "entry.605237767": selected_q5 if selected_q5 else ["Không có lo ngại gì đặc biệt"],
        "entry.518529063": random.choices(q6_options, weights=q6_weights)[0],
        "entry.804096739": random.choices(q7_options, weights=q7_weights)[0],
        "entry.1930033278": random.choices(q8_options, weights=q8_weights)[0],
        "entry.2044483679": random.choices(q9_options, weights=q9_weights)[0],
        "fvv": "1",
        "draftResponse": "[null,null,\"-7398399057092063546\"]",
        "pageHistory": "0",
        "fbzx": "-7398399057092063546"
    }
    return response

def submit_to_google_form(data):
    """Sends a single response to the Google Form via POST."""
    try:
        res = requests.post(FORM_URL, data=data)
        if res.status_code == 200:
            print("Successfully submitted response.")
        else:
            print(f"Failed to submit. Status code: {res.status_code}")
    except Exception as e:
        print(f"An error occurred: {e}")

def run_simulation(num_records=5, delay=1):
    """Generates and submits multiple responses with a slight delay."""
    for i in range(num_records):
        print(f"Submitting response {i+1}/{num_records}...")
        payload = generate_weighted_responses()
        submit_to_google_form(payload)
        time.sleep(delay) # Delay to avoid being flagged as a bot

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Submit weighted survey responses to Google Forms.")
    parser.add_argument("--records", type=int, default=5, help="Number of submissions")
    parser.add_argument("--delay", type=float, default=1.5, help="Delay in seconds between submissions")
    args = parser.parse_args()

    run_simulation(num_records=args.records, delay=args.delay)