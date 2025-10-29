from transformers import pipeline
from PIL import Image
import requests
import numpy as np

# load pipe
pipe = pipeline(task="depth-estimation", model="depth-anything/Depth-Anything-V2-Small-hf")

# load image
url = 'http://images.cocodataset.org/val2017/000000039769.jpg'
image = Image.open(requests.get(url, stream=True).raw)

# inference
#pipe(image['predicted_depth']) gives depth predictions for each pixel in meters
depth = pipe(image)["depth"]

depth.save("test.jpg")

#depth = im.frombytes()



#Image.crop(coords) for selecting the sign area