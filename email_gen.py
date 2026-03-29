import random
from faker import Faker
from unidecode import unidecode

# Initialize Faker with Vietnamese locale
fake = Faker('vi_VN')

def generate_varied_vn_emails(count=15):
    print(f"--- Generating {count} Short, Medium, & Long @google.com Emails ---\n")
    
    results = []
    departments = ['dev', 'ops', 'hr', 'sales', 'mkt', 'tech']
    
    # Define our length styles and their "weights" (probability)
    # 20% Short, 50% Medium, 30% Long
    styles = ['short', 'medium', 'long']
    weights = [20, 50, 30]
    
    for _ in range(count):
        style = random.choices(styles, weights=weights)[0]
        
        if style == 'short':
            # e.g., "linh.nguyen.45"
            handle = f"{fake.user_name()}.{random.randint(10, 99)}"
        
        elif style == 'medium':
            # e.g., "tran.anh.1995"
            ln = unidecode(fake.last_name()).lower()
            fn = unidecode(fake.first_name()).lower()
            year = random.randint(1980, 2010)
            handle = f"{ln}.{fn}.{year}"
        
        else: # Long
            # e.g., "nguyen.van.hoang.anh.tech.1992"
            full_name = unidecode(fake.name()).lower().replace(" ", ".")
            dept = random.choice(departments)
            year = random.randint(1985, 2005)
            handle = f"{full_name}.{dept}.{year}"
        
        email = f"{handle}@google.com"
        results.append(email)
        print(f"[{style.upper():<6}] {email}")
        
    return results

if __name__ == "__main__":
    generate_varied_vn_emails(15)