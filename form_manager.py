
import json
import os
import re
import csv

class FormManager:
    def __init__(self) -> None:
        self._surveys_file = "surveys/surveys.json"
        self._surveys = self.load_surveys()
        self._formatted_surveys = []
        self._survey_links = []
        print("Form Manager initialized...")
        print("Form Manager's surveys file set to 'surveys/surveys.json'")

    @property
    def embed_codes(self) -> list:
        return self._embed_codes
    
    @embed_codes.setter
    def embed_codes(self, embed_codes) -> None:
        self._embed_codes = embed_codes

    @property
    def surveys(self) -> list:
        return self._surveys
    
    @surveys.setter
    def surveys(self, surveys) -> None:
        self._surveys = surveys
    
    @property
    def formatted_surveys(self) -> list:
        return self._formatted_surveys
    
    @formatted_surveys.setter
    def formatted_urls(self, formatted_urls) -> None:
        self._formatted_urls = formatted_urls
    
    @formatted_surveys.deleter
    def formatted_surveys(self) -> None:
        self._formatted_surveys = []

    def add_survey(self, survey_name, survey_url, folder) -> None:
        """
        Adds a survey to the list of surveys.
        Current functionality is a modification of the original function to store survey links in a JSON file.
        If the old functionality is needed, comment out the blocks of code that are marked with a comment and
        uncomment everything else.  
        """
        # url = self.customize_form_url(survey_url, subject_id)

        # COMMENT NEXT BLOCK IF OLD FUNCTIONALITY IS NEEDED
        survey_links_file = os.path.join(folder, "survey_links.json")
        if not os.path.exists(survey_links_file):
            with open(survey_links_file, "w") as file:
                json.dump({"surveys": []}, file)

        survey = {
            "name": survey_name,
            "url": survey_url
        }

        if self._surveys and survey not in self._surveys:
            # self._surveys.append(survey)
            # with open(self._surveys_file, "w") as file:
            #     json.dump({"surveys": self._surveys}, file, indent=4)

            # COMMENT NEXT BLOCK IF OLD FUNCTIONALITY IS NEEDED
            self._survey_links.append(survey)
            with open(survey_links_file, "w") as file:
                json.dump({"surveys: ": self._survey_links}, file, indent=4)
            
        else:
            print("Survey already exists.")

    def clean_string(self, value) -> str:
        outstring = value.lower().replace(' ', '_').strip()
        outstring = re.sub(r"[^a-zA-Z0-9_\-]", "", outstring)
        return outstring
    
    def find_survey(self, infile, subject_manager) -> bool:
        """
        Searches for a survey entry that matches the subject's details and writes the filtered data to a new CSV file.
        Args:
            infile (file-like object): The input CSV file containing survey data.
            subject_manager (object): An object containing subject details such as first name, last name, email, ID, and data folder.
        Returns:
            bool: True if the subject is found in the survey data and the filtered data is written to a new CSV file, False otherwise.
        Raises:
            ValueError: If the required columns ("First Name", "Last Name", "Email") are not found in the CSV headers.
        Notes:
            - The method assumes that the input CSV file has headers and that the headers include "First Name", "Last Name", and "Email".
            - The method writes the filtered data to a new CSV file named with the subject's ID and the original filename in the subject's data folder.
        """

        filename = infile.filename
        subject_first_name = subject_manager.subject_first_name
        subject_last_name = subject_manager.subject_last_name
        subject_email = subject_manager.subject_email
        subject_id = subject_manager.subject_id
        subject_data_folder = subject_manager.subject_folder

        with open(infile, 'r', newline='', encoding='utf-8') as infile:
            reader = csv.reader(infile)
            headers = next(reader)
            timestamp_idx = 0
            first_name_idx = headers.index("First Name")
            last_name_idx = headers.index("Last Name")
            email_idx = headers.index("Email")

            new_headers = ["Timestamp"] + [col for i, col in enumerate(headers) if i not in (first_name_idx, last_name_idx, email_idx)]
            output_csv = os.path.join(f"{subject_data_folder}", f"{subject_id}_{filename}")

            with open(output_csv, mode='w', newline='', encoding='utf-8') as outfile:
                writer = csv.writer(outfile)
                writer.writerow(new_headers)

                for row in reader:
                    csv_first_name = self.clean_string(row[first_name_idx])
                    csv_last_name = self.clean_string(row[last_name_idx])
                    csv_email = row[email_idx].lower().strip().replace(" ", "_")    

                    if(csv_first_name == subject_first_name and csv_last_name == subject_last_name and csv_email == subject_email):
                        filtered_row = [row[timestamp_idx]] + [row[i] for i in range(len(row)) if i not in (first_name_idx, last_name_idx, email_idx)]
                        writer.writerow(filtered_row)
                        return True
                    else:
                        print("Subject not found in survey data.")
                        return False

    def remove_survey(self, survey_name) -> None:
        for survey in self._surveys:
            if survey["name"] == survey_name:
                self._surveys.remove(survey)

        with open(self._surveys_file, "w") as file:
            json.dump({"surveys": self._surveys}, file, indent=4)

    def customize_form_url(self, url, subject_id) -> str:
        """
        Replaces 'Sample+ID' in a Google Forms URL with the provided subject_id.
        Parameters:
            url (str): The Google Forms URL containing 'Sample+ID' as a placeholder.
            subject_id (str): The value to replace 'Sample+ID'.
        Returns:
            str: The updated URL with 'Sample+ID' replaced by subject_id.
        """
        if not url.strip(): 
            return url

        subject_id = subject_id.replace(" ", "+")
        updated_url = url.replace("Sample+ID", subject_id)

        return updated_url

    def autofill_forms(self, subject_id) -> None:
        formatted_surveys = []
        print(f"Autofilling forms for ID: {subject_id}")
        if self.surveys:
            for survey in self.surveys:
                url = self.customize_form_url(survey["url"], subject_id)
                formatted_survey = {
                    "name": survey["name"],
                    "url": url
                }
                print(url)
                formatted_surveys.append(formatted_survey)

            self.surveys = formatted_surveys
            del self.formatted_surveys
        else:
            raise ValueError("No surveys to autofill.")
    
    def load_surveys(self) -> list:
        if not os.path.exists(self._surveys_file):
            raise FileNotFoundError(f"{self._surveys_file} does not exist.")
        else:
            with open(self._surveys_file, "r") as file:
                survey_data = json.load(file)
                surveys = survey_data.get("surveys", [])
                return surveys
            
    def get_survey_url(self, survey_name: str) -> str:
        surveys = self.load_surveys()
        for survey in surveys:
            if survey["name"] == survey_name:
                return survey["url"]
        return f"Survey with name '{survey_name}' not found."
    
    def get_custom_url(self, survey_name: str, subject_id: str) -> str:
        """
        Retrieves the URL for the given survey and customizes it with the subject's name and ID.

        Parameters:
            survey_name (str): The name of the survey to retrieve the URL for.
            subject_id (str): The ID of the subject to be inserted into the URL.

        Returns:
            str: The customized URL for the specified survey.
        """
        survey_url = self.get_survey_url(survey_name)

        if survey_url is None: 
            return f"Survey with name '{survey_name}' not found."  
        
        return self.customize_form_url(survey_url, subject_id)