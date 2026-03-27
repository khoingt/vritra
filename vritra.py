import os
import yaml
import random
import time
import argparse
import requests
from tqdm import tqdm
from dotenv import load_dotenv

load_dotenv()

class FormEngine:
    def __init__(self, config_path):
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)
        
        self.form_id = self.config.get('form_id')
        self.url = f"https://docs.google.com/forms/d/e/{self.form_id}/formResponse"
        self.sections = {s['id']: s for s in self.config['sections']}
        self.section_order = [s['id'] for s in self.config['sections']]

    def get_answer(self, question):
        q_type = question.get('type')
        
        if q_type == "radio":
            options = [opt['text'] for opt in question['options']]
            weights = [opt['weight'] for opt in question['options']]
            choice = random.choices(question['options'], weights=weights)[0]
            return choice['text'], choice.get('routing', 'continue')

        elif q_type == "checkbox":
            selected = []
            for opt in question['options']:
                if random.random() < opt['probability']:
                    selected.append(opt['text'])
            
            if not selected and 'default_if_none' in question:
                selected.append(question['default_if_none'])
            
            return selected, "continue"

        elif q_type == "text":
            return random.choice(question['text_pool']), "continue"

        return None, "continue"

    def simulate_entry(self):
        answers = {}
        current_history = ""
        fbzx = str(random.randint(10**18, 10**19))
        
        # Step through sections
        idx = 0
        while idx < len(self.section_order):
            section_id = self.section_order[idx]
            section = self.sections[section_id]
            current_history = section['page_history']
            
            section_routing = "continue"
            
            for q in section['questions']:
                val, route = self.get_answer(q)
                answers[q['id']] = val
                # If any question triggers a non-continue route, we track it
                if route != "continue":
                    section_routing = route

            # Handle Routing Logic
            if section_routing.startswith("terminate:"):
                term_history = section_routing.split(":")[1]
                return self.submit(answers, term_history, fbzx), "fail"
            
            if section_routing == "submit":
                return self.submit(answers, current_history, fbzx), "pass"
            
            if section_routing.startswith("goto:"):
                target_id = section_routing.split(":")[1]
                idx = self.section_order.index(target_id)
                continue
            
            idx += 1
            
        return self.submit(answers, current_history, fbzx), "pass"

    def submit(self, answers, history, fbzx):
        payload = {
            "fvv": "1",
            "pageHistory": history,
            "fbzx": fbzx,
            "submissionTimestamp": str(int(time.time() * 1000))
        }
        
        for q_id, val in answers.items():
            if isinstance(val, list):
                # Handle checkboxes (multiple entries for same ID)
                payload[q_id] = val
            else:
                payload[q_id] = val
            payload[f"{q_id}_sentinel"] = ""

        try:
            response = requests.post(self.url, data=payload, timeout=10)
            return response.status_code == 200
        except:
            return False

def run(args):
    engine = FormEngine(args.config)
    stats = {"pass": 0, "fail": 0, "error": 0}
    
    print(f"Targeting Form: {engine.form_id}")
    
    for _ in tqdm(range(args.simulations), desc="Simulating", unit="user"):
        success, state = engine.simulate_entry()
        
        if success:
            stats[state] += 1
        else:
            stats["error"] += 1
            
        # Human Jitter logic
        jitter = random.uniform(args.delay * 0.5, args.delay * 1.5)
        time.sleep(jitter)

    print(f"\n--- Simulation Results ---")
    print(f"Successful Passes: {stats['pass']}")
    print(f"Screened Out:      {stats['fail']}")
    print(f"Network Errors:    {stats['error']}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--config", required=True, help="Path to the YAML config file")
    parser.add_argument("-n", "--simulations", type=int, default=5)
    parser.add_argument("-d", "--delay", type=float, default=3.0)
    args = parser.parse_args()
    run(args)