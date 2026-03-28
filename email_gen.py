import random
from faker import Faker
from unidecode import unidecode

# Initialize Faker with Vietnamese locale
fake = Faker('vi_VN')

def generate_mixed_vn_emails(count=15):
    print(f"--- Generating {count} Mixed Vietnamese @google.com Emails ---\n")
    
    results = []
    departments = ['dev', 'ops', 'hr', 'sales', 'legal', 'mkt']
    
    for _ in range(count):
        # Choose a style: 0 for Short, 1 for Long
        style = random.choice(['short', 'long'])
        
        if style == 'short':
            # Style 1: Simple username + random 2-digit number
            # e.g., "linh.nguyen.92@google.com"
            handle = f"{fake.user_name()}.{random.randint(10, 99)}"
        
        else:
            # Style 2: Full name + Department + Year
            # e.g., "pham.thi.tuyet.mai.legal.1988@google.com"
            full_name = unidecode(fake.name()).lower().replace(" ", ".")
            dept = random.choice(departments)
            year = random.randint(1980, 2005)
            handle = f"{full_name}.{dept}.{year}"
        
        email = f"{handle}@google.com"
        results.append(email)
        print(f"[{style.upper()}] {email}")
        
    return results

if __name__ == "__main__":
    generate_mixed_vn_emails(15)