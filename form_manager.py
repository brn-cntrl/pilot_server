
import json
import os
import re
import csv

class FormManager:
    def __init__(self) -> None:
        self._surveys_file = "surveys/surveys.json"
        self._surveys = self.load_surveys()
        self._formatted_surveys = []
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

    def add_survey(self, survey_name, survey_url) -> None:
        """
        Adds a survey to the list of surveys.
        Current functionality is a modification of the original function to store survey links in a JSON file.
        If the old functionality is needed, comment out the blocks of code that are marked with a comment and
        uncomment everything else.  
        """
        survey_data = self.load_surveys()
        if survey_data is None:
            print("Survey file missing.")
            return("Survey file missing.")

        surveys = survey_data.get("surveys", [])
        survey = {
            "name": survey_name,
            "url": survey_url
        }

        if survey not in surveys:
            surveys.append(survey)
            print("Survey added.")

            if self._surveys_file:
                with open(self._surveys_file, "w") as file:
                    json.dump({"surveys": surveys}, file, indent=4)
                return "Success"
            else:
                print("Survey already exists.")
                return "Survey already exists."

    def clean_string(self, value) -> str:
        outstring = value.lower().replace(' ', '_').strip()
        outstring = re.sub(r"[^a-zA-Z0-9_\-]", "", outstring)
        return outstring
    
    def get_survey_url(self, name):
        """
        Retrieve the URL of a survey by its name.
        Args:
            name (str): The name of the survey to find.
        Returns:
            str: The URL of the survey if found, otherwise "Survey not found".
        """
        surveys = self.load_surveys()
        survey = next((s for s in surveys if s["name"] == name), None)
        if not survey:
            return "Survey not found"
        else:
            return survey["url"]

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
                print(f"Survey found: {survey_name}")
                return survey["url"]
            
        return "not found"
    
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