import os
import json
import requests
import logging
from dotenv import load_dotenv
import asyncio
import re
import traceback

# Настройка логирования
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)

load_dotenv()

logger = logging.getLogger(__name__)

def clean_json_text(text: str) -> str:
    """Очистка текста от дополнительного форматирования и извлечение JSON"""
    # Удаляем \boxed{ и другие специальные символы
    text = re.sub(r'\\boxed{', '', text)
    text = re.sub(r'\\[^{]+{', '', text)  # Удаляем другие LaTeX команды
    
    # Удаляем маркеры кода
    text = re.sub(r'```json\s*', '', text)
    text = re.sub(r'```\s*', '', text)
    text = text.strip()
    
    # Находим все возможные JSON объекты
    json_candidates = []
    depth = 0
    start = -1
    
    for i, char in enumerate(text):
        if char == '{':
            if depth == 0:
                start = i
            depth += 1
        elif char == '}':
            depth -= 1
            if depth == 0 and start != -1:
                json_candidate = text[start:i+1]
                try:
                    # Проверяем, что это валидный JSON
                    json.loads(json_candidate)
                    json_candidates.append(json_candidate)
                except json.JSONDecodeError:
                    pass
    
    if json_candidates:
        # Берем самый длинный валидный JSON
        return max(json_candidates, key=len)
    
    # Если не нашли валидный JSON, пробуем найти вручную
    start = text.find('{')
    end = text.rfind('}') + 1
    if start != -1 and end != 0:
        json_text = text[start:end]
        # Удаляем лишние закрывающие скобки в конце
        while json_text.count('{') < json_text.count('}'):
            json_text = json_text[:-1]
        return json_text
    
    return text

def generate_llm_response(prompt: str) -> dict:
    """Генерация ответа через OpenRouter API"""
    try:
        logger.info("Начинаем запрос к OpenRouter API")
        logger.info(f"Промпт: {prompt}")
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {os.getenv('OPENROUTER_API_KEY')}"
        }
        
        payload = {
            "model": "deepseek/deepseek-r1-zero:free",
            "messages": [
                {
                    "role": "system",
                    "content": "Ты - эксперт по созданию реалистичных профилей респондентов для customer development интервью. Твои ответы должны быть в формате JSON."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        }
        
        logger.info("Отправка запроса к API...")
        logger.info(f"URL: https://openrouter.ai/api/v1/chat/completions")
        logger.info(f"Headers: {json.dumps(headers, ensure_ascii=False)}")
        logger.info(f"Payload: {json.dumps(payload, ensure_ascii=False, indent=2)}")
        
        response = requests.post(
            url="https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=60
        )
        
        logger.info(f"Получен ответ от API. Статус: {response.status_code}")
        logger.info(f"Заголовки ответа: {dict(response.headers)}")
        logger.info(f"Тело ответа: {response.text}")
        
        if response.status_code == 200:
            result = response.json()
            logger.debug(f"Полный ответ API: {json.dumps(result, indent=2, ensure_ascii=False)}")
            
            # Пробуем разные варианты получения контента
            content = None
            try:
                if 'choices' in result and len(result['choices']) > 0:
                    message = result['choices'][0].get('message', {})
                    content = message.get('content') or message.get('reasoning')
                elif 'response' in result:
                    content = result['response']
                
                if not content:
                    logger.error(f"Не удалось найти контент в ответе API: {result}")
                    return {"error": "Неверный формат ответа API", "details": "Отсутствует контент в ответе"}
                    
                logger.debug(f"Извлеченный контент: {content}")
            except Exception as e:
                logger.error(f"Ошибка при извлечении контента: {str(e)}")
                logger.error(f"Структура ответа: {result}")
                return {"error": "Ошибка при обработке ответа API", "details": str(e)}
            
            # Очищаем текст от форматирования
            clean_content = clean_json_text(content)
            logger.debug(f"Очищенный JSON: {clean_content}")
            
            try:
                profile_data = json.loads(clean_content)
                logger.info("JSON успешно обработан")
                
                # Проверяем наличие всех необходимых полей
                required_fields = ["name", "age", "profession", "pain_points", "communication_style", "traps"]
                missing_fields = [field for field in required_fields if field not in profile_data]
                
                if missing_fields:
                    return {
                        "error": "Неполный профиль",
                        "details": f"Отсутствуют поля: {', '.join(missing_fields)}",
                        "raw_content": clean_content
                    }
                
                return profile_data
                
            except json.JSONDecodeError as e:
                logger.error(f"Ошибка при парсинге JSON: {str(e)}")
                logger.error(f"Проблемный текст: {clean_content}")
                return {
                    "error": "Ошибка при создании профиля",
                    "details": str(e),
                    "raw_content": clean_content
                }
        else:
            logger.error(f"Ошибка API: {response.status_code}")
            return {"error": f"Ошибка API: {response.status_code}", "details": response.text}
            
    except Exception as e:
        logger.error(f"Неожиданная ошибка: {str(e)}")
        logger.error(traceback.format_exc())
        return {"error": "Неожиданная ошибка", "details": str(e)}

async def generate_responder(age: int, profession: str, trait: str) -> dict:
    """Генерация профиля респондента"""
    prompt = f"""
    Создай профиль респондента со следующими характеристиками:
    - Возраст: {age} лет
    - Профессия: {profession}
    - Характер: {trait}

    Сгенерируй JSON-профиль в следующем формате:
    {{
        "name": "реалистичное русское имя",
        "age": число,
        "profession": "профессия",
        "pain_points": ["3-4 ключевые боли"],
        "communication_style": "2-3 предложения о стиле общения",
        "traps": ["3-4 способа, как респондент уходит от прямых ответов"]
    }}
    """
    
    try:
        response = generate_llm_response(prompt)
        
        if "error" in response:
            logger.error(f"Ошибка при генерации профиля: {response}")
            return {
                "success": False,
                "message": f"❌ Произошла ошибка при создании респондента: {response['error']}"
            }
            
        # Форматируем сообщение для пользователя
        message = f"""✅ Респондент успешно создан!

👤 {response['name']}
📊 Возраст: {response['age']}
💼 Профессия: {response['profession']}

🎭 Стиль общения:
{response['communication_style']}

❗️ Ключевые боли:
""" + "\n".join(f"• {point}" for point in response['pain_points']) + """

⚠️ Возможные ловушки в общении:
""" + "\n".join(f"• {trap}" for trap in response['traps']) + """

Теперь вы можете начать интервью. Введите свой вопрос:"""
        
        return {
            "success": True,
            "message": message,
            "data": response
        }
        
    except Exception as e:
        logger.error(f"Ошибка при создании респондента: {str(e)}")
        logger.error(traceback.format_exc())
        return {
            "success": False,
            "message": "❌ Произошла непредвиденная ошибка при создании респондента. Попробуйте еще раз."
        }

async def generate_interview_response(question: str, respondent_profile: dict) -> str:
    """Генерация ответа на вопрос в интервью с учетом профиля респондента"""
    try:
        prompt = f"""
        Ты - респондент со следующим профилем:
        Имя: {respondent_profile['name']}
        Возраст: {respondent_profile['age']}
        Профессия: {respondent_profile['profession']}
        Стиль общения: {respondent_profile['communication_style']}
        
        Твои болевые точки:
        {chr(10).join('- ' + point for point in respondent_profile['pain_points'])}
        
        Твои паттерны уклонения от прямых ответов:
        {chr(10).join('- ' + trap for trap in respondent_profile['traps'])}
        
        Вопрос: {question}
        
        Ответь на вопрос в соответствии со своим профилем, используя указанный стиль общения и случайным образом применяя один из паттернов уклонения. Ответ должен быть реалистичным и отражать твои болевые точки.
        """
        
        logger.info(f"Генерация ответа на вопрос: {question}")
        response = generate_llm_response(prompt)
        
        # Извлекаем текст ответа
        content = response['choices'][0]['message'].get('content', '')
        reasoning = response['choices'][0]['message'].get('reasoning', '')
        answer = content if content else reasoning
        
        # Очищаем ответ от возможных JSON-маркеров и других артефактов
        clean_answer = re.sub(r'```.*?```', '', answer, flags=re.DOTALL)  # Удаляем код между ```
        clean_answer = re.sub(r'\{.*?\}', '', clean_answer, flags=re.DOTALL)  # Удаляем JSON
        clean_answer = clean_answer.strip()
        
        logger.info(f"Сгенерирован ответ: {clean_answer}")
        return clean_answer
        
    except Exception as e:
        logger.error(f"Ошибка при генерации ответа на вопрос: {str(e)}")
        logger.error(traceback.format_exc())
        return f"Извините, произошла ошибка при генерации ответа: {str(e)}"

if __name__ == "__main__":
    # Тестируем сначала простой запрос
    try:
        logger.info("Тестирование API с простым запросом...")
        test_response = generate_llm_response("Скажи привет")
        logger.info("Тестовый запрос успешен")
        logger.info(f"Ответ: {json.dumps(test_response, ensure_ascii=False, indent=2)}")
    except Exception as e:
        logger.error(f"Тестовый запрос не удался: {str(e)}")
    
    # Если простой запрос успешен, тестируем генерацию профиля
    logger.info("\nТестирование генерации профиля...")
    test_profile = asyncio.run(generate_responder(35, "Product Manager", "скептик"))
    print(json.dumps(test_profile, ensure_ascii=False, indent=2))
    
    # Тестируем генерацию ответа на вопрос
    if "error" not in test_profile:
        logger.info("\nТестирование генерации ответа на вопрос...")
        test_question = "Как вы принимаете решения о новых функциях продукта?"
        test_answer = asyncio.run(generate_interview_response(test_question, test_profile))
        print(f"\nВопрос: {test_question}")
        print(f"Ответ: {test_answer}") 