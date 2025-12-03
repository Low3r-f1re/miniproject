const TRANSLATIONS = {
  en: {
    "discover-amazing-places": "Discover Amazing Places",
    "explore-breathtaking-destinations": "Explore breathtaking destinations, plan unforgettable trips, and create memories around the world with TourWithMe.",
    "get-started": "Get Started Free",
    "why-choose-us": "Why Choose Us?",
    "global-destinations": "Global Destinations",
    "interactive-maps": "Interactive Maps",
    "budget-planning": "Budget Planning"
  },
  hi: {
    "discover-amazing-places": "अद्भुत जगहें खोजें",
    "explore-breathtaking-destinations": "TourWithMe के साथ दुनिया भर के शानदार गंतव्यों का अन्वेषण करें, अविस्मरणीय यात्राओं की योजना बनाएं, और स्मृतियां बनाएं।",
    "get-started": "मुफ्त में शुरू करें",
    "why-choose-us": "हमें क्यों चुनें?",
    "global-destinations": "वैश्विक गंतव्य",
    "interactive-maps": "इंटरैक्टिव मैप्स",
    "budget-planning": "बजट योजना"
  },
  kn: {
    "discover-amazing-places": "ಅದ್ಭುತ ಸ್ಥಳಗಳನ್ನು ಕಂಡುಹಿಡಿಯಿರಿ",
    "explore-breathtaking-destinations": "TourWithMe ಜೊತೆಗೆ ವಿಶ್ವದ ಸುತ್ತಮುತ್ತಲಿನ ಆಶ್ಚರ್ಯಕರ ಗಮ್ಯಸ್ಥಾನಗಳನ್ನು ಅನ್ವೇಷಿಸಿ, ಮರೆಯಲಾಗದ ಪ್ರಯಾಣಗಳನ್ನು ಯೋಜಿಸಿ, ಮತ್ತು ಸ್ಮರಣೆಗಳನ್ನು ರಚಿಸಿ.",
    "get-started": "ಮುಕ್ತವಾಗಿ ಪ್ರಾರಂಭಿಸಿ",
    "why-choose-us": "ನಾವನ್ನು ಯಾಕೆ ಆಯ್ಕೆಮಾಡುವುದು?",
    "global-destinations": "ಜಾಗತಿಕ ಗಮ್ಯಸ್ಥಾನಗಳು",
    "interactive-maps": "ಪರಸ್ಪರ ಕಾರ್ಯನಿರ್ವಹಿಸುವ ನಕ್ಷೆಗಳು",
    "budget-planning": "ಬಜೆಟ್ ಯೋಜನೆ"
  }
};

// Function to change language
function changeLanguage(lang) {
  const elementsToTranslate = document.querySelectorAll('[data-translate]');
  elementsToTranslate.forEach(element => {
    const key = element.getAttribute('data-translate');
    element.textContent = TRANSLATIONS[lang][key] || element.textContent;
  });
}

document.addEventListener('DOMContentLoaded', function() {
  // Example usage
  const languageSelector = document.getElementById('language-select');
  if (languageSelector) {
    languageSelector.addEventListener('change', function() {
      changeLanguage(this.value);
    });
  }

  // Translate page based on session language
  const lang = document.body.getAttribute('lang') || 'en';
  changeLanguage(lang);

  // Fetch translations from server if needed
  fetch('/static/translations/' + lang + '.json')
    .then(response => response.json())
    .then(data => {
      TRANSLATIONS[lang] = { ...TRANSLATIONS[lang], ...data };
      changeLanguage(lang);
    })
    .catch(error => console.error('Error loading translations:', error));
});
