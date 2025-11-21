import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
import string # To remove punctuation

# --- NEW: List of all categories for dropdowns ---
# We define this here so it's in one central place.
CATEGORIES_KEYWORDS = {
    'Transport': {
        'uber', 'lyft', 'ola', 'rapido', 'taxi', 'auto', 'rickshaw', 
        'subway', 'metro', 'bus', 'train', 'airline', 'flight', 'airways', 'indigo', 'vistara',
        'gas', 'fuel', 'petrol', 'diesel', 'cng', 'parking', 'toll', 'fastag', 'airport'
    },
    'Food & Groceries': {
        'food', 'grocery', 'groceries', 'restaurant', 'cafe', 'coffee', 'meal', 'lunch', 'dinner', 'breakfast',
        'supermarket', 'walmart', 'target', 'costco', 'kroger', 'bigbasket', 'blinkit', 'zepto', 'grofers',
        'swiggy', 'zomato', 'ubereats', 'doordash', 'pizza', 'burger', 'sushi', 'starbucks', 'ccd', 'delivery', 'receipt','ate'
    },
    'Health & Wellness': {
        'health', 'pharmacy', 'doctor', 'hospital', 'medical', 'clinic', 'dentist', 'medicine',
        'cvs', 'walgreens', 'apollo', 'medplus', 'netmeds', 'pharmeasy', 'wellness',
        'gym', 'fitness', 'cult.fit', 'yoga', 'vitamins', 'supplement'
    },
    'Utilities & Bills': {
        'utility', 'electric', 'electricity', 'power', 'water', 'internet', 'phone', 'bill',
        'comcast', 'verizon', 'att', 'airtel', 'jio', 'vi', 'vodafone', 'broadband', 'wifi',
        'gas', 'sewage', 'recharge', 'mobile', 'postpaid', 'prepaid'
    },
    'Entertainment & Subscriptions': {
        'entertainment', 'movie', 'movies', 'cinema', 'tickets', 'bookmyshow', 'paytm', 'pvr', 'inox',
        'spotify', 'netflix', 'hulu', 'amazon', 'prime', 'disney', 'hotstar', 'zee5', 'sony', 'youtube',
        'concert', 'game', 'games', 'steam', 'playstation', 'psn', 'xbox', 'nintendo', 'premium'
    },
    'Shopping & Personal': {
        'shopping', 'clothes', 'clothing', 'apparel', 'shoes', 'fashion',
        'amazon', 'flipkart', 'myntra', 'ajio', 'nykaa', 'meesho', 'trends', 'lifestyle', 'mall', 'store',
        'electronics', 'gadget', 'apple', 'samsung', 'croma', 'reliance', 'digital'
    },
    'Housing & Rent': {
        'rent', 'mortgage', 'emi', 'loan', 'housing', 'apartment', 'maintenance', 'property', 'tax', 'realtor'
    },
    'Insurance': {
        'insurance', 'lic', 'policy', 'premium', 'bajaj', 'allianz', 'hdfc', 'ergo', 'icici', 'lombard'
    },
    'Personal Care': {
        'salon', 'haircut', 'barber', 'cosmetics', 'toiletries', 'beauty', 'parlour', 'spa', 'grooming'
    },
    'Education': {
        'tuition', 'school', 'college', 'university', 'books', 'stationery', 'udemy', 'coursera', 'fee', 'fees'
    },
    'Gifts & Donations': {
        'gift', 'donation', 'charity', 'present', 'birthday', 'wedding', 'unicef', 'give', 'ngo'
    },
    'Fees & Charges': {
        'fee', 'charge', 'bank', 'atm', 'withdrawal', 'late', 'penalty', 'interest', 'service'
    },
    'Investments & Savings': {
        'investment', 'mutual', 'fund', 'sip', 'stocks', 'equity', 'zerodha', 'groww', 'upstox', 'crypto'
    },
    'Travel': {
        'travel', 'hotel', 'booking.com', 'makemytrip', 'mmt', 'goibibo', 'airbnb', 'yatra', 'vacation', 'holiday'
    },
    'Other': {'other'} # Default
}

# --- NEW: Exportable list of all categories ---
ALL_CATEGORIES = ['Income'] + list(CATEGORIES_KEYWORDS.keys())
# --- End of new list ---


try:
    STOP_WORDS = set(stopwords.words('english'))
except LookupError:
    nltk.download('stopwords')
    STOP_WORDS = set(stopwords.words('english'))

PUNCTUATION = set(string.punctuation)

def categorize_expense(description, income_expense_type):
    """
    Assigns a category to a transaction using NLTK for tokenization and stopword removal.
    """
    if income_expense_type == 'Income':
        return 'Income'
    
    try:
        tokens = word_tokenize(str(description).lower())
        
        cleaned_tokens = set()
        for token in tokens:
            if token not in STOP_WORDS and token not in PUNCTUATION and token.isalpha():
                cleaned_tokens.add(token)
                
    except Exception as e:
        cleaned_tokens = set(str(description).lower().split())

    
    for category, keywords in CATEGORIES_KEYWORDS.items():
        if not cleaned_tokens.isdisjoint(keywords):
            return category
            
    return 'Other'