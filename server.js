const express = require("express");
const Database = require("better-sqlite3");
const cors = require("cors");
const path = require("path");

const app = express();
app.use(cors());
app.use(express.json());
app.use(express.static(path.join(__dirname, "public")));

const db = new Database("reports.db");
db.exec(`CREATE TABLE IF NOT EXISTS reports (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  lat REAL NOT NULL,
  lng REAL NOT NULL,
  location_name TEXT,
  bloom_date TEXT NOT NULL,
  note TEXT,
  created_at TEXT DEFAULT (datetime('now','localtime'))
)`);

app.get("/api/reports", (req, res) => {
  const rows = db.prepare("SELECT * FROM reports ORDER BY created_at DESC").all();
  res.json(rows);
});

app.post("/api/reports", (req, res) => {
  const { lat, lng, location_name, bloom_date, note } = req.body;
  if (!lat || !lng || !bloom_date) return res.status(400).json({ error: "lat, lng, bloom_date 필수" });
  const info = db.prepare(
    "INSERT INTO reports (lat, lng, location_name, bloom_date, note) VALUES (?,?,?,?,?)"
  ).run(lat, lng, location_name || "", bloom_date, note || "");
  res.json({ id: info.lastInsertRowid });
});

app.delete("/api/reports/:id", (req, res) => {
  db.prepare("DELETE FROM reports WHERE id = ?").run(req.params.id);
  res.json({ ok: true });
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => console.log(`Server running on port ${PORT}`));
