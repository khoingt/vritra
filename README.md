# Google Forms Response Simulator

This Python script is designed to simulate human-like survey submissions for a specific Google Form structure. It uses weighted probabilities to generate realistic data and mimics the multi-step network behavior of a browser.

---

## How the Script Works

The script operates by replicating the exact HTTP POST requests that a web browser sends when a user interacts with a Google Form. It follows three primary logic phases:

1. Instead of purely random selection, the script uses a weighted distribution for each question. This ensures the final dataset reflects specific trends (for example, ensuring 85 percent of respondents are regular players).
2. The script identifies if a respondent fails the initial screening question. If they are disqualified, it sends two sequential requests to mimic the "Continue" and "End of Survey" flow. If they pass, it submits the full dataset with the appropriate page history markers.
3. To avoid being flagged as automated traffic, the script includes "Human Jitter." This adds a randomized delay between submissions so that the timing between requests is inconsistent, much like a real person filling out a form.

---

## Prerequisites

Before running the script, ensure you have Python installed along with the following libraries:

* **requests**: To handle the HTTP communication with Google servers.
* **python-dotenv**: To securely manage the Form ID.
* **tqdm**: To provide a visual progress bar in the terminal.

You can install these dependencies using the following command:
pip install requests python-dotenv tqdm

---

## Configuration

1. Create a file named `.env` in the root directory of the script.
2. Add your Google Form ID to the file using the following format:
   FORM_ID=your_actual_form_id_here

Note: The Form ID is the long string of characters found in the URL of the form (located between /d/e/ and /viewform).

---

## Usage

You can execute the script from your terminal. It supports two optional arguments to customize the simulation:

* **-n or --simulations**: The total number of responses you wish to submit.
* **-d or --delay**: The baseline delay in seconds between each submission.

**Example Command:**
python script.py --simulations 50 --delay 5.0

This command will run 50 simulations with a randomized delay centered around 5 seconds.

---

## Summary Report

Upon completion, the script will display a summary in the terminal. This report includes the total number of attempts, the count of users who passed the screening, and the count of users who were disqualified.