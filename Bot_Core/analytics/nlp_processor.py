from keybert import KeyBERT
from typing import List, Dict, Tuple
import numpy as np
from collections import Counter

class NLPProcessor:
    def __init__(self):
        self.model = KeyBERT('distilbert-base-nli-mean-tokens')
        self.threshold = 0.3  # Порог релевантности для ключевых слов

    def extract_keywords(self, text: str, top_n: int = 5) -> List[Tuple[str, float]]:
        """Извлечение ключевых слов из текста"""
        keywords = self.model.extract_keywords(
            text,
            keyphrase_ngram_range=(1, 2),
            stop_words='russian',
            top_n=top_n
        )
        return keywords

    def analyze_response(self, response: str, hypothesis_keywords: List[str]) -> Dict:
        """Анализ ответа респондента"""
        # Извлекаем ключевые слова из ответа
        response_keywords = self.extract_keywords(response)
        
        # Проверяем соответствие гипотезе
        relevance_scores = []
        for h_keyword in hypothesis_keywords:
            max_score = 0
            for r_keyword, score in response_keywords:
                if h_keyword.lower() in r_keyword.lower():
                    max_score = max(max_score, score)
            relevance_scores.append(max_score)
        
        avg_relevance = np.mean(relevance_scores)
        
        return {
            "keywords": [kw for kw, _ in response_keywords],
            "relevance_score": avg_relevance,
            "is_relevant": avg_relevance > self.threshold
        }

    def detect_bias(self, responses: List[str]) -> Dict:
        """Определение возможных искажений в ответах"""
        all_keywords = []
        for response in responses:
            keywords = self.extract_keywords(response)
            all_keywords.extend([kw for kw, _ in keywords])
        
        # Подсчет частоты ключевых слов
        keyword_freq = Counter(all_keywords)
        
        # Определение потенциальных искажений
        biases = []
        for keyword, freq in keyword_freq.items():
            if freq / len(responses) > 0.7:  # Если слово встречается в >70% ответов
                biases.append({
                    "keyword": keyword,
                    "frequency": freq / len(responses)
                })
        
        return {
            "total_responses": len(responses),
            "potential_biases": biases
        }

    def generate_insights(self, responses: List[str], hypothesis: str) -> Dict:
        """Генерация инсайтов на основе ответов"""
        hypothesis_keywords = [kw for kw, _ in self.extract_keywords(hypothesis)]
        
        relevant_responses = 0
        key_insights = []
        
        for response in responses:
            analysis = self.analyze_response(response, hypothesis_keywords)
            if analysis["is_relevant"]:
                relevant_responses += 1
                if analysis["relevance_score"] > 0.5:  # Высоко релевантные ответы
                    key_insights.append(response[:200] + "...")  # Берем первые 200 символов
        
        return {
            "confirmation_rate": relevant_responses / len(responses),
            "key_insights": key_insights[:3],  # Топ-3 инсайта
            "hypothesis_keywords": hypothesis_keywords
        }

if __name__ == "__main__":
    # Пример использования
    processor = NLPProcessor()
    
    # Тестовые данные
    hypothesis = "Бухгалтеры тратят много времени на ручной ввод данных"
    responses = [
        "Да, приходится постоянно вручную вбивать цифры, это занимает уйму времени",
        "Автоматизация? Нет, мы все делаем руками, так надежнее",
        "Мне кажется, это не проблема, просто нужно быть внимательнее"
    ]
    
    # Анализ
    insights = processor.generate_insights(responses, hypothesis)
    print("Инсайты:", insights)
    
    bias_report = processor.detect_bias(responses)
    print("Отчет по искажениям:", bias_report) 