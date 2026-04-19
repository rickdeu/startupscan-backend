import logging
from ..commom_imports import (
    np, pd, tqdm,
    GradientBoostingRegressor, RandomForestRegressor,
    train_test_split, cross_val_score,
    mean_squared_error, r2_score,
    confusion_matrix, ConfusionMatrixDisplay,
    SimpleImputer, StandardScaler, Pipeline,
    ensure_plot_imports, plt,
)
from .features import prepare_features

try:
    from ..commom_imports import XGBRegressor
except ImportError:
    XGBRegressor = None


def train_and_evaluate(df, financial_df, progress_callback=None):
    X, y, metadata = [], [], []

    for idx, row in tqdm(df.iterrows(), total=len(df), desc="A treinar o modelo: "):
        financial_idx = idx % len(financial_df)
        financial_row = (
            financial_df.iloc[financial_idx]
            if isinstance(financial_df, pd.DataFrame)
            else financial_df[financial_idx]
        )
        features, meta = prepare_features(row, financial_row)
        X.append(features)
        y.append(row.get('success_score', 5.0) if hasattr(row, 'get') else row.get('success_score', 5.0))
        metadata.append(meta)

    X = np.array(X)
    y = np.array(y)

    model = Pipeline([
        ('imputer', SimpleImputer(strategy='mean')),
        ('scaler', StandardScaler()),
        ('regressor', GradientBoostingRegressor(
            n_estimators=100,
            learning_rate=0.1,
            max_depth=3,
            random_state=42,
        )),
    ])

    if len(X) > 1:
        scores = cross_val_score(model, X, y, cv=min(5, len(X)), scoring='r2')
        logging.info(f"R2 médio na validação cruzada: {np.mean(scores):.2f} (±{np.std(scores):.2f})")

    model.fit(X, y)
    return model, metadata


def train_with_random_forest(df, financial_df):
    ensure_plot_imports()
    X, y, metadata = [], [], []

    for idx, row in tqdm(df.iterrows(), total=len(df), desc="Treinando com Random Forest"):
        financial_idx = idx % len(financial_df)
        financial_row = (
            financial_df.iloc[financial_idx]
            if isinstance(financial_df, pd.DataFrame)
            else financial_df[financial_idx]
        )
        features, meta = prepare_features(row, financial_row)
        X.append(features)
        y.append(row.get('success_score', 5.0))
        metadata.append(meta)

    X = np.array(X)
    y = np.array(y)
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    model = Pipeline([
        ('imputer', SimpleImputer(strategy='mean')),
        ('scaler', StandardScaler()),
        ('regressor', RandomForestRegressor(n_estimators=100, random_state=42)),
    ])
    model.fit(X_train, y_train)
    predictions = model.predict(X_test)

    mse = mean_squared_error(y_test, predictions)
    r2 = r2_score(y_test, predictions)
    logging.info(f"Random Forest - MSE: {mse:.2f}, R2: {r2:.2f}")

    if plt is not None:
        plt.figure()
        plt.scatter(y_test, predictions, alpha=0.7)
        plt.plot([min(y_test), max(y_test)], [min(y_test), max(y_test)], 'r--')
        plt.xlabel('Valor Real')
        plt.ylabel('Predição')
        plt.title('Random Forest: Real vs Previsto')
        plt.grid(True)
        plt.show()

        y_true_class = np.clip(np.round(y_test), 1, 10).astype(int)
        y_pred_class = np.clip(np.round(predictions), 1, 10).astype(int)
        cm = confusion_matrix(y_true_class, y_pred_class, labels=range(1, 11))
        disp = ConfusionMatrixDisplay(confusion_matrix=cm, display_labels=range(1, 11))
        disp.plot(cmap=plt.cm.Blues, values_format='d')
        plt.title("Matriz de Confusão Multiclasse - Random Forest")
        plt.show()

    return model, metadata


def train_with_xgboost(df, financial_df):
    ensure_plot_imports()
    if XGBRegressor is None:
        raise ImportError("XGBoost não instalado. Use: pip install xgboost")

    X, y, metadata = [], [], []

    for idx, row in tqdm(df.iterrows(), total=len(df), desc="Treinando com XGBoost"):
        financial_idx = idx % len(financial_df)
        financial_row = (
            financial_df.iloc[financial_idx]
            if isinstance(financial_df, pd.DataFrame)
            else financial_df[financial_idx]
        )
        features, meta = prepare_features(row, financial_row)
        X.append(features)
        y.append(row.get('success_score', 5.0))
        metadata.append(meta)

    X = np.array(X)
    y = np.array(y)
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.25, random_state=42)

    model = Pipeline([
        ('imputer', SimpleImputer(strategy='mean')),
        ('scaler', StandardScaler()),
        ('regressor', XGBRegressor(
            n_estimators=100, learning_rate=0.1, max_depth=4, random_state=42
        )),
    ])
    model.fit(X_train, y_train)
    predictions = model.predict(X_test)

    mse = mean_squared_error(y_test, predictions)
    r2 = r2_score(y_test, predictions)
    logging.info(f"XGBoost - MSE: {mse:.2f}, R2: {r2:.2f}")

    if plt is not None:
        plt.figure()
        plt.scatter(y_test, predictions, alpha=0.6, color='orange')
        plt.plot([min(y_test), max(y_test)], [min(y_test), max(y_test)], 'b--')
        plt.xlabel("Real")
        plt.ylabel("Previsto")
        plt.title("XGBoost: Real vs Previsto")
        plt.grid(True)
        plt.show()

        y_true_class = np.clip(np.round(y_test), 1, 10).astype(int)
        y_pred_class = np.clip(np.round(predictions), 1, 10).astype(int)
        cm = confusion_matrix(y_true_class, y_pred_class, labels=range(1, 11))
        disp = ConfusionMatrixDisplay(confusion_matrix=cm, display_labels=range(1, 11))
        disp.plot(cmap=plt.cm.Blues, values_format='d')
        plt.title("Matriz de Confusão Multiclasse - XGBoost")
        plt.show()

    return model, metadata
