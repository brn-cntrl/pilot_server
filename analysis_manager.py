import psycopg2

class AnalysisManager:
    def __init__(self):
        self.conn = psycopg2.connect("dbname=analysis user=analysis password=analysis")
        self.cur = self.conn.cursor()

    def get_analysis(self, analysis_id):
        self.cur.execute("SELECT * FROM analysis WHERE id = %s", (analysis_id,))
        return self.cur.fetchone()

    def get_analyses(self):
        self.cur.execute("SELECT * FROM analysis")
        return self.cur.fetchall()

    def create_analysis(self, data):
        self.cur.execute("INSERT INTO analysis (data) VALUES (%s) RETURNING id", (data,))
        return self.cur.fetchone()[0]

    def delete_analysis(self, analysis_id):
        self.cur.execute("DELETE FROM analysis WHERE id = %s", (analysis_id,))
        self.conn.commit()

    def __del__(self):
        self.cur.close()
        self.conn.close()