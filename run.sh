virtualenv cutter
source cutter/bin/activate

conda install ffmpeg -c conda-forge

pip install -r requirements.txt

python app.py

 