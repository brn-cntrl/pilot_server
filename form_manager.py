
import json
import os
import re

class FormManager:
    def __init__(self) -> None:
        self._surveys_file = "surveys.json"
        self._surveys = self.load_surveys()
        self._formatted_surveys = []

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
        # url = self.customize_form_url(survey_url, subject_name, subject_id)
        survey = {
            "name": survey_name,
            "url": survey_url
        } 
        if self._surveys and survey not in self._surveys:
            self._surveys.append(survey)
            with open(self._surveys_file, "w") as file:
                json.dump({"surveys": self._surveys}, file, indent=4)
        else:
            print("Survey already exists.")

    def remove_survey(self, survey_name) -> None:
        for survey in self._surveys:
            if survey["name"] == survey_name:
                self._surveys.remove(survey)

        with open(self._surveys_file, "w") as file:
            json.dump({"surveys": self._surveys}, file, indent=4)

    def customize_form_url(self, url, subject_name, subject_id) -> str:
        """
        Replaces placeholder values in a URL dynamically without regex or urllib.

        Parameters:
            url (str): The URL containing dynamic placeholders.
            subject_name (str): The value to replace the first placeholder.
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

        # Iterate through the query parameters and replace placeholders
        for pair in query_pairs:
            if "entry." in pair and "=" in pair:
                key, value = pair.split("=", 1)
                if placeholder_count == 0:
                    value = subject_name  # Replace first placeholder
                    placeholder_count += 1
                elif placeholder_count == 1:
                    value = subject_id  # Replace second placeholder
                    placeholder_count += 1
                # Reconstruct the updated pair
                updated_pairs.append(f"{key}={value}")
            else:
                # Keep the pair unchanged
                updated_pairs.append(pair)

        # Reconstruct the full URL
        updated_query_string = "&".join(updated_pairs)
        updated_url = f"{base_url}?{updated_query_string}"

        return updated_url
    
    def autofill_forms(self, subject_name, subject_id) -> None:
        formatted_surveys = []
        print(f"Autofilling forms for {subject_name} with ID: {subject_id}")
        if self.surveys:
            for survey in self.surveys:
                url = self.customize_form_url(survey["url"], subject_name, subject_id)
                formatted_survey = {
                    "name": survey["name"],
                    "url": url
                }
                print(url)
                formatted_surveys.append(formatted_survey)

            # Reassign formatted surveys to surveys
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