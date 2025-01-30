
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
    
    def clean_survey_info(self, infile, survey_name, subject_manager) -> None:
        if infile.endswith('.csv'):
            subject_first_name = subject_manager.subject_first_name
            subject_last_name = subject_manager.subject_last_name
            subject_id = subject_manager.subject_id
            subject_data_folder = subject_manager.subject_folder

            # Open the csv file for reading
            with open(infile, 'r', newline='', encoding='utf-8') as infile:
                # Look for the headers
                reader = csv.reader(infile)
                header = next(reader)

                first_name_idx = header.index("First Name")
                last_name_idx = header.index("Last Name")
                email_idx = header.index("Email")

                outfile = os.path.join(f"{subject_data_folder}", f"{subject_id}_{survey_name}.csv")
                with open(outfile, mode='w', newline='', encoding='utf-8') as outfile:
                    writer = csv.writer(outfile)
                    new_header = ['Subject ID'] + header
                    writer.writerow(new_header)

                    for row in reader:
                        csv_first_name = self.clean_string(row[first_name_idx])
                        csv_last_name = self.clean_string(row[last_name_idx])
                        csv_email = row[email_idx]

                        if(csv_first_name == subject_first_name and 
                           csv_last_name == subject_last_name and 
                           csv_email == subject_manager.subject_email):
                            row_with_id = [subject_id] + row
                            writer.writerow(row_with_id)
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
        Replaces placeholder values in a URL dynamically without regex or urllib.

        Parameters:
            url (str): The URL containing dynamic placeholders.
            subject_id (str): The value to replace the second placeholder.

        Returns:
            str: The updated URL with placeholders replaced dynamically.
        """
        if not url.strip(): 
            return url

        if "?" in url:
            base_url, query_string = url.split("?", 1)
        else:
            return url  

        query_pairs = query_string.split("&")
        updated_pairs = []
        placeholder_count = 0

        for pair in query_pairs:
            if "entry." in pair and "=" in pair:
                key, value = pair.split("=", 1)
                if placeholder_count == 0:
                    value = subject_id  
                    placeholder_count += 1
                # elif placeholder_count == 1:
                #     value = subject_id  
                    # placeholder_count += 1
                updated_pairs.append(f"{key}={value}")
            else:
                updated_pairs.append(pair)

        # Reconstruct the full URL
        updated_query_string = "&".join(updated_pairs)
        updated_url = f"{base_url}?{updated_query_string}"

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
    
    # def  _code(self, survey_name) -> str:
    #     return_value = ""
    #     for survey in self.surveys:
    #         if survey["name"] == survey_name:
    #             return_value = f'<iframe src="{survey["url"]}" width="920" height="680"></iframe>'
    #             return return_value
    #         else:
    #             return_value = f"<p>Survey with name '{survey_name}' not found.</p>"
                
    #     return return_value
    
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
