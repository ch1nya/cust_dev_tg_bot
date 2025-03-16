from typing import Dict, List, Union

class ProfileValidator:
    def __init__(self):
        self.profession_tools = {
            "бухгалтер": ["1C", "Excel", "SAP", "Контур.Бухгалтерия"],
            "дизайнер": ["Figma", "Photoshop", "Illustrator", "Sketch"],
            "разработчик": ["VS Code", "PyCharm", "Git", "Docker"],
            "product manager": ["Jira", "Confluence", "Miro", "Notion"]
        }

    def validate_profile(self, profile: Dict) -> Dict[str, Union[Dict, List[str]]]:
        """Валидация профиля респондента"""
        errors = []
        warnings = []

        # Проверка обязательных полей
        required_fields = ["name", "age", "profession", "pain_points", "communication_style", "traps"]
        for field in required_fields:
            if field not in profile:
                errors.append(f"Отсутствует обязательное поле: {field}")

        if errors:
            return {
                "status": "error",
                "profile": profile,
                "errors": errors
            }

        # Проверка возраста
        if profile["age"] < 18 or profile["age"] > 80:
            warnings.append("Подозрительный возраст респондента")

        # Проверка количества pain points
        if len(profile["pain_points"]) < 2:
            warnings.append("Слишком мало болевых точек")
        elif len(profile["pain_points"]) > 5:
            warnings.append("Слишком много болевых точек")

        # Проверка количества traps
        if len(profile["traps"]) < 2:
            warnings.append("Слишком мало паттернов уклонения")
        elif len(profile["traps"]) > 5:
            warnings.append("Слишком много паттернов уклонения")

        # Проверка длины communication_style
        if len(profile["communication_style"].split()) < 5:
            warnings.append("Слишком короткое описание стиля общения")

        return {
            "status": "success" if not warnings else "warning",
            "profile": profile,
            "warnings": warnings
        }

    def check_profession_bias(self, profile: Dict) -> List[str]:
        """Проверка на профессиональные стереотипы"""
        biases = []
        profession = profile["profession"].lower()

        # Проверка инструментов если они указаны
        if "tools" in profile:
            expected_tools = self.profession_tools.get(profession, [])
            if expected_tools:
                found_tools = [tool for tool in profile["tools"] if tool in expected_tools]
                if not found_tools:
                    biases.append(f"Нетипичный набор инструментов для профессии {profession}")

        return biases

if __name__ == "__main__":
    # Пример использования
    validator = ProfileValidator()
    test_profile = {
        "name": "Иван Петров",
        "age": 35,
        "profession": "бухгалтер",
        "pain_points": ["Сложная отчетность", "Много ручной работы"],
        "communication_style": "Говорит медленно, часто переспрашивает",
        "traps": ["Уходит в детали", "Ссылается на опыт"],
        "tools": ["Excel", "1C"]
    }
    
    result = validator.validate_profile(test_profile)
    print("Результат валидации:", result)
    
    biases = validator.check_profession_bias(test_profile)
    print("Обнаруженные биасы:", biases) 