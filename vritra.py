import os
import random
import argparse
import time
import requests
from tqdm import tqdm
from dotenv import load_dotenv

load_dotenv()
FORM_ID = os.getenv("FORM_ID")

if not FORM_ID:
    print("Error: FORM_ID not found in .env file.")
    exit(1)

FORM_URL = f"https://docs.google.com/forms/d/e/{FORM_ID}/formResponse"

def generate_weighted_responses():
    # Q1: Screening Question
    q1_options = ["Có, tôi chơi thường xuyên (ít nhất 1 lần mỗi tuần)", "Thỉnh thoảng (1 đến 3 lần mỗi tháng)", "Hiếm khi hoặc không bao giờ"]
    q1_weights = [85.5, 10.5, 4.0]
    q1_answer = random.choices(q1_options, weights=q1_weights)[0]

    if q1_answer == "Hiếm khi hoặc không bao giờ":
        return {
            "type": "fail",
            "q1_answer": q1_answer,
            "fbzx": str(random.randint(10**18, 10**19)) 
        }

    # Main Survey Questions
    q5_choices = [
        ("Phụ kiện có thể bị tuột hoặc lỏng trong khi chơi", 0.45),
        ("Độ bám vẫn không đủ tốt so với giày đá bóng thật", 0.22),
        ("Khó gắn hoặc tháo trong thực tế", 0.14),
        ("Trông không đẹp hoặc kỳ lạ khi đeo", 0.08),
        ("Giá thành quá cao", 0.06),
        ("Không có lo ngại gì đặc biệt", 0.05)
    ]
    selected_q5 = [opt for opt, weight in q5_choices if random.random() < weight]

    return {
        "type": "pass",
        "fbzx": str(random.randint(10**18, 10**19)),
        "data": {
            "entry.213754659": q1_answer,
            "entry.623712297": random.choices(["Có, điều này thường xuyên gây khó chịu cho tôi", "Có, nhưng tôi không coi đó là vấn đề lớn", "Không, tôi không cảm thấy bất tiện"], weights=[70.2, 20.4, 9.4])[0],
            "entry.1483251668": random.choices(["Có, tôi vẫn chơi dù biết có thể bị trơn trượt", "Có, nhưng tôi chơi cẩn thận hơn bình thường", "Không, tôi chờ đến khi có giày phù hợp mới chơi"], weights=[15.3, 65.2, 19.5])[0],
            "entry.453496296": random.choices(["Rất quan tâm, tôi muốn thử ngay", "Quan tâm, nhưng tôi cần biết thêm thông tin", "Không chắc chắn", "Không quan tâm"], weights=[28.4, 52.1, 10.5, 9.0])[0],
            "entry.1763230376": selected_q5 if selected_q5 else ["Không có lo ngại gì đặc biệt"],
            "entry.614858321": random.choices(["Có, tôi hoàn toàn tin tưởng", "Có thể, nhưng tôi cần dùng thử trước", "Không chắc chắn", "Không, tôi vẫn không tin tưởng dù được đảm bảo chắc chắn"], weights=[22.8, 48.2, 20.5, 8.5])[0],
            "entry.205766033": random.choices(["Tiện lợi hơn nhiều so với mang thêm giày", "Tiện lợi hơn một chút", "Không có sự khác biệt đáng kể", "Kém tiện lợi hơn so với mang thêm giày"], weights=[35.4, 45.3, 10.2, 9.1])[0],
            "entry.768782966": random.choices(["Dưới 100.000 VND", "Từ 100.000 đến 200.000 VND", "Từ 200.000 đến 400.000 VND", "Trên 400.000 VND", "Tôi sẽ không mua dù ở mức giá nào"], weights=[52.7, 30.1, 10.2, 4.0, 3.0])[0],
            "entry.1117461758": random.choices(["Có, tôi sẽ mua ngay", "Có thể, tôi sẽ cân nhắc thêm", "Không, tôi sẽ không mua"], weights=[45, 40, 15])[0],
        }
    }

def submit_logic(response):
    fbzx = response["fbzx"]
    ts = str(int(time.time() * 1000))

    if response["type"] == "fail":
        # Request 1: Continue
        payload1 = {
            "entry.213754659": response["q1_answer"], "entry.213754659_sentinel": "",
            "fvv": "1", "partialResponse": f"[null,null,\"{fbzx}\"]",
            "pageHistory": "0", "fbzx": fbzx, "submissionTimestamp": "-1", "continue": "1"
        }
        requests.post(FORM_URL, data=payload1)
        
        # Request 2: Screened Out Submit
        payload2 = {
            "fvv": "1", "partialResponse": f"[[[null,213754659,[\"{response['q1_answer']}\"],0]],null,\"{fbzx}\"]",
            "pageHistory": "0,-3", "fbzx": fbzx, "submissionTimestamp": ts
        }
        requests.post(FORM_URL, data=payload2)
        return "fail"

    else:
        # Full Pass Submit
        full_data = response["data"]
        full_data.update({"fvv": "1", "pageHistory": "0,1", "fbzx": fbzx, "submissionTimestamp": ts})
        for key in list(full_data.keys()):
            if "entry" in key: full_data[f"{key}_sentinel"] = ""
        
        requests.post(FORM_URL, data=full_data)
        return "pass"

def run_simulation(num_records, base_delay):
    stats = {"pass": 0, "fail": 0}
    print(f"Targeting Form: {FORM_ID}")
    
    for _ in tqdm(range(num_records), desc="Submitting Responses", unit="resp"):
        res = generate_weighted_responses()
        status = submit_logic(res)
        stats[status] += 1
        
        # Human Jitter: base_delay +/- 50% randomness
        jitter = random.uniform(base_delay * 0.5, base_delay * 1.5)
        time.sleep(jitter)

    print(f"\n--- Done ---\nPassed: {stats['pass']}\nFailed: {stats['fail']}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-n", "--simulations", type=int, default=5)
    parser.add_argument("-d", "--delay", type=float, default=3.0)
    args = parser.parse_args()

    run_simulation(args.simulations, args.delay)