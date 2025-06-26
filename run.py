# run.py
from app import create_app

app = create_app()

if __name__ == '__main__':
    # You can now re-enable the reloader if you wish
    app.run(debug=True) 