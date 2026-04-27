import os
import tensorflow as tf
from tensorflow.keras.preprocessing.image import ImageDataGenerator
from tensorflow.keras.applications import MobileNetV2
from tensorflow.keras.layers import Dense, GlobalAveragePooling2D, Dropout
from tensorflow.keras.models import Model
from tensorflow.keras.optimizers import Adam

# Config
TRAIN_DIR = "dataset/train" 
VAL_DIR = "dataset/validation"
IMG_SIZE = (224, 224)
BATCH_SIZE = 32
EPOCHS = 10
MODEL_SAVE_PATH = "model/waste_model.h5"

def build_model(num_classes):
    # Load base model with pre-trained weights
    base_model = MobileNetV2(weights='imagenet', include_top=False, input_shape=(224, 224, 3))
    
    # UNFREEZE top layers for fine-tuning (Key for 95%+ accuracy)
    base_model.trainable = True
    for layer in base_model.layers[:-30]: # Freeze first 120+ layers, train the last 30
        layer.trainable = False

    x = base_model.output
    x = GlobalAveragePooling2D()(x)
    x = Dense(512, activation='relu')(x) # Increased capacity
    x = Dropout(0.4)(x) 
    predictions = Dense(num_classes, activation='softmax')(x)

    model = Model(inputs=base_model.input, outputs=predictions)
    # Using a lower learning rate for fine-tuning
    model.compile(optimizer=Adam(learning_rate=0.0001), 
                  loss='categorical_crossentropy', 
                  metrics=['accuracy'])
    return model

def main():
    if not os.path.exists(TRAIN_DIR):
        print(f"Error: {TRAIN_DIR} not found. Run prepare_datasets.py first.")
        return

    print("Loading and augmenting data...")
    train_datagen = ImageDataGenerator(
        rescale=1./255,
        rotation_range=20,
        width_shift_range=0.2,
        height_shift_range=0.2,
        shear_range=0.2,
        zoom_range=0.2,
        horizontal_flip=True
    )
    
    val_datagen = ImageDataGenerator(rescale=1./255)

    train_generator = train_datagen.flow_from_directory(
        TRAIN_DIR,
        target_size=IMG_SIZE,
        batch_size=BATCH_SIZE,
        class_mode='categorical'
    )

    val_generator = val_datagen.flow_from_directory(
        VAL_DIR,
        target_size=IMG_SIZE,
        batch_size=BATCH_SIZE,
        class_mode='categorical'
    )

    num_classes = train_generator.num_classes
    print(f"Found {num_classes} classes: {list(train_generator.class_indices.keys())}")

    model = build_model(num_classes)

    print("Starting training...")
    history = model.fit(
        train_generator,
        epochs=EPOCHS,
        validation_data=val_generator
    )

    os.makedirs(os.path.dirname(MODEL_SAVE_PATH), exist_ok=True)
    model.save(MODEL_SAVE_PATH)
    print(f"Model saved to {MODEL_SAVE_PATH}")
    
    import json
    with open('model/class_indices.json', 'w') as f:
        json.dump(train_generator.class_indices, f)

if __name__ == '__main__':
    main()
