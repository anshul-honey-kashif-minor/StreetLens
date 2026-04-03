import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.svm import LinearSVC
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, accuracy_score

df = pd.read_csv("category - Sheet1.csv")

X = df['text']
y = df['label']

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=99)

vectorizer = TfidfVectorizer(analyzer="char", ngram_range=(3,5))

X_train_vec = vectorizer.fit_transform(X_train)
X_test_vec = vectorizer.transform(X_test)

X_vec = vectorizer.fit_transform(X)

model = LinearSVC()

model.fit(X_train_vec, y_train)

predictions = model.predict(X_test_vec)

print("Accuracy:", accuracy_score(y_test, predictions))

