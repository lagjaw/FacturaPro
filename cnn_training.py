import tensorflow as tf
import os
from tensorflow.keras import layers, models
from tensorflow.keras.callbacks import EarlyStopping, ModelCheckpoint

train_path = os.path.join("dataset/train/")
test_path = os.path.join("dataset/test/")


if not os.path.exists(train_path):
    print(f"Training directory '{train_path}' does not exist.")
    exit()  # Stop execution if the directory does not exist

# Function to create the CNN model
def create_cnn_model(input_shape):
    model = models.Sequential([
        layers.Input(shape=input_shape),  # Add Input layer
        layers.Conv2D(32, (3, 3), activation='relu'),
        layers.MaxPooling2D(pool_size=(2, 2)),
        layers.Conv2D(64, (3, 3), activation='relu'),
        layers.MaxPooling2D(pool_size=(2, 2)),
        layers.Conv2D(128, (3, 3), activation='relu'),
        layers.MaxPooling2D(pool_size=(2, 2)),
        layers.Flatten(),
        layers.Dense(128, activation='relu'),
        layers.Dense(1, activation='sigmoid')
    ])
    model.compile(optimizer='adam', loss='binary_crossentropy', metrics=['accuracy'])
    return model

def check_images_in_directory(train_path):
    allowed_extensions = ('.bmp', '.gif', '.jpeg', '.jpg', '.png')
    images = [f for f in os.listdir(train_path) if f.lower().endswith(allowed_extensions)]
    if not images:
        raise ValueError(f"No images found in directory {train_path}. Allowed formats: {allowed_extensions}")
    return images


# Verify images in the training directory
try:
    train_images = check_images_in_directory(train_path)
    print("Found training images:", train_images)
except ValueError as e:
    print(e)
    exit()  # Stop execution if no images are found

def train_model(model, train_path, image_size=(256, 256), batch_size=32):
    # Load training dataset with validation split
    train_ds = tf.keras.preprocessing.image_dataset_from_directory(
        train_path,
        image_size=image_size,
        batch_size=batch_size,
        validation_split=0.2,  # Split 20% for validation
        subset='training',
        seed=123
    )

    val_ds = tf.keras.preprocessing.image_dataset_from_directory(
        train_path,
        image_size=image_size,
        batch_size=batch_size,
        validation_split=0.2,
        subset='validation',
        seed=123
    )

    # Configure early stopping and model checkpointing
    early_stopping = EarlyStopping(monitor='val_loss', patience=3)
    model_checkpoint = ModelCheckpoint("best_model.h5", save_best_only=True, monitor='val_loss')

    # Train the model
    history = model.fit(train_ds, validation_data=val_ds, epochs=10, callbacks=[early_stopping, model_checkpoint])

    # Evaluate the model
    train_loss, train_accuracy = model.evaluate(train_ds)
    val_loss, val_accuracy = model.evaluate(val_ds)

    #Print Value

    return {
        "train_accuracy": train_accuracy,
        "train_loss": train_loss,
        "val_accuracy": val_accuracy,
        "val_loss": val_loss,
        "history": history.history
    }

    print(train_accuracy)
    print(train_loss)
    print(val_loss)
    print(history)

# Example usage
if __name__ == "__main__":
    input_shape = (256, 256, 3)  # Adjust based on your image size and channels
    cnn_model = create_cnn_model(input_shape)
    results = train_model(cnn_model, train_path)
    print(results)

