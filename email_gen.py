import random
from faker import Faker
from unidecode import unidecode

# Initialize Faker with Vietnamese locale
fake = Faker('vi_VN')

def generate_pro_vn_emails(count=15):
    print(f"--- Generating {count} Authentic & Long @google.com Emails ---\n")
    
    results = []
    departments = ['marketing', 'solutions', 'engineering', 'operation', 'consultant']
    
    for _ in range(count):
        # 1. Generate a full Vietnamese name (e.g., "Trần Thị Tuyết")
        full_name = fake.name()
        
        # 2. Strip accents and convert to lowercase
        # "Trần Thị Tuyết" -> "Tran Thi Tuyet" -> "tran.thi.tuyet"
        clean_name = unidecode(full_name).lower().replace(" ", ".")
        
        # 3. Add extra length components
        dept = random.choice(departments)
        year = random.randint(1985, 2005)
        
        # 4. Construct the final long email
        email = f"{clean_name}.{dept}.{year}@google.com"
        
        results.append(email)
        print(email)
        
    return results

if __name__ == "__main__":
    generate_pro_vn_emails(15)