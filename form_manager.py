
import json
import os

class FormManager:
    def __init__(self) -> None:
        self._surveys_file = "surveys.json"
        self._surveys = self.load_surveys()

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
        
    def add_survey(self, survey_name, survey_url) -> None:
        # url = self.customize_form_url(survey_url, subject_name, subject_id)
        survey = {
            "name": survey_name,
            "url": survey_url
        } 
        if self._surveys and survey not in self._surveys:
            self._surveys.append(survey)

    def remove_survey(self, survey_name) -> None:
        for survey in self._surveys:
            if survey["name"] == survey_name:
                self._surveys.remove(survey)

    def customize_form_url(self, url, subject_name, subject_id) -> str:
        """
        Customize the default form URL by replacing the subject name and ID
        - Parameters:
            - subject_name: The name of the subject
            - subject_id: The ID of the subject
        - Returns:
            - The customized form URL
        """
        base_url, _, query_string = url.partition('?')
        query_params = [param.split('=') for param in query_string.split('&') if '=' in param]

        if len(query_params) > 0:
            query_params[0][1] = subject_name
        if len(query_params) > 1:
            query_params[1][1] = subject_id

        updated_query_string = '&'.join(f"{key}={value}" for key, value in query_params)

        return f"{base_url}?{updated_query_string}"
    
    def autofill_forms(self, subject_name, subject_id) -> None:
        formatted_surveys = []
        if self.surveys:
            for survey in self.surveys:
                url = self.customize_form_url(survey["url"], subject_name, subject_id)
                formatted_survey = {
                    "name": survey["name"],
                    "url": url
                }
                formatted_surveys.append(formatted_survey)
                self.surveys = formatted_surveys
                print(f"Autofilled form for {survey['name']}: {url}")
        else:
            raise ValueError("No surveys to autofill.")
    
    def get_embed_code(self, survey_name) -> str:
        return_value = ""
        for survey in self.surveys:
            if survey["name"] == survey_name:
                return_value = f'<iframe src="{survey["url"]}" width="920" height="680"></iframe>'
                return return_value
            else:
                return_value = f"Survey with name '{survey_name}' not found."
                
        return return_value
    
    def load_surveys(self) -> list:
        if not os.path.exists(self._surveys_file):
            raise FileNotFoundError(f"{self._surveys_file} does not exist.")
        else:
            with open(self._surveys_file, "r") as file:
                survey_data = json.load(file)
                surveys = survey_data.get("surveys", [])
                return surveys