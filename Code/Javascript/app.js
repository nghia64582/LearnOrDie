// app.js

const express = require('express');
const mysql = require('mysql2');
const moment = require('moment');
const app = express();
const port = process.env.PORT || 3000;

app.use(express.json());

const DB_HOST = 'nghia64582.online'
const DB_USER = 'qrucoqmt_nghia64582'
const DB_PASSWORD = 'Nghi@131299'
const DB_NAME = 'qrucoqmt_nghia64582'

let dbConnection = null;

const createDbConnection = () => {
    return mysql.createConnection({
        host: DB_HOST,
        user: DB_USER,
        password: DB_PASSWORD,
        database: DB_NAME
    });
};

const connectToDatabase = () => {
    dbConnection = createDbConnection();
    dbConnection.connect(err => {
        if (err) {
            console.error('Error connecting to MySQL database:', err);
            dbConnection = null;
            return;
        }
        console.log('Successfully connected to MySQL database');
    });
};

const withConnection = (handler) => async (req, res) => {
    let connection;
    try {
        connection = createDbConnection();
        await handler(req, res, connection);
    } catch (error) {
        console.error('Database connection or query error:', error);
        res.status(500).json({ status: "error", message: `Database error: ${error.message}` });
    } finally {
        if (connection) connection.end();
    }
};

app.get('/', (req, res) => {
    res.send('Hello, World!');
});

app.get('/db_test', withConnection(async (req, res, connection) => {
    const [rows] = await connection.execute("SELECT VERSION()");
    if (rows && rows.length > 0) {
        res.json({
            status: "success",
            message: "Successfully connected to database!",
            mysql_version: rows[0]['VERSION()']
        });
    } else {
        res.status(500).json({
            status: "error",
            message: "Connected but could not fetch database version."
        });
    }
}));

app.get('/create_table', withConnection(async (req, res, connection) => {
    const createTableSql = `
        CREATE TABLE IF NOT EXISTS \`key_value_store\` (
            \`id\` INT(11) NOT NULL AUTO_INCREMENT PRIMARY KEY,
            \`key\` VARCHAR(255) NOT NULL UNIQUE,
            \`value\` TEXT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
            KEY \`key_index\` (\`key\`)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
    `;
    await connection.execute(createTableSql);
    res.json({
        status: "success",
        message: "Table 'key_value_store' created or already exists."
    });
}));

app.post('/store/:key', withConnection(async (req, res, connection) => {
    const key = req.params.key;
    const { value } = req.body;
    if (!value) {
        return res.status(400).json({ status: "error", message: "Missing 'value' in request body." });
    }

    const [rows] = await connection.execute("SELECT `key` FROM `key_value_store` WHERE `key` = ?", [key]);
    if (rows.length > 0) {
        await connection.execute("UPDATE `key_value_store` SET `value` = ? WHERE `key` = ?", [value, key]);
        res.json({ status: "success", message: "Key-value pair updated successfully.", key, value });
    } else {
        await connection.execute("INSERT INTO `key_value_store` (`key`, `value`) VALUES (?, ?)", [key, value]);
        res.json({ status: "success", message: "Key-value pair stored successfully.", key, value });
    }
}));

app.get('/retrieve/:key', withConnection(async (req, res, connection) => {
    const key = req.params.key;
    const [rows] = await connection.execute("SELECT `value` FROM `key_value_store` WHERE `key` = ?", [key]);
    if (rows.length > 0) {
        res.json({ status: "success", key, value: rows[0].value });
    } else {
        res.status(404).json({ status: "error", message: `Key '${key}' not found.` });
    }
}));

app.delete('/delete/:key', withConnection(async (req, res, connection) => {
    const key = req.params.key;
    const [result] = await connection.execute("DELETE FROM `key_value_store` WHERE `key` = ?", [key]);
    if (result.affectedRows > 0) {
        res.json({ status: "success", message: `Key '${key}' deleted successfully.` });
    } else {
        res.status(404).json({ status: "error", message: `Key '${key}' not found or already deleted.` });
    }
}));

app.get("/hello", (req, res) => {
    res.send("Hello, World! This is 2.0");
});

app.get("/all_keys", withConnection(async (req, res, connection) => {
    const [rows] = await connection.execute("SELECT `key` FROM `key_value_store`");
    const keys = rows.map(row => row.key);
    res.json({ status: "success", keys });
}));

app.set('trust proxy', true);
app.get("/ip", (req, res) => {
    const ipAddress = req.ip;
    res.json({
        status: "success",
        message: "Your IP address is:",
        ip_address: ipAddress
    });
});

app.get('/record', withConnection(async (req, res, connection) => {
    const { 'start-time': startTimeStr, 'end-time': endTimeStr } = req.query;

    if (!startTimeStr || !endTimeStr) {
        return res.status(400).json({ error: "Missing 'start-time' or 'end-time' parameters." });
    }

    try {
        const startDate = moment(startTimeStr, 'DD-MM-YYYY').startOf('day').format('YYYY-MM-DD HH:mm:ss');
        const endDate = moment(endTimeStr, 'DD-MM-YYYY').endOf('day').format('YYYY-MM-DD HH:mm:ss');
        const [rows] = await connection.execute("SELECT id, name, score, created_at FROM extraunary WHERE created_at BETWEEN ? AND ?", [startDate, endDate]);
        const records = rows.map(row => ({
            id: row.id,
            name: row.name,
            score: row.score,
            created_at: moment(row.created_at).format('YYYY-MM-DD')
        }));
        res.json(records);
    } catch (error) {
        res.status(400).json({ error: "Invalid date format. Please use 'dd-mm-yyyy'." });
    }
}));

app.get('/record-by-name', withConnection(async (req, res, connection) => {
    const nameToSearch = req.query.name;
    if (!nameToSearch) {
        return res.status(400).json({ error: "Missing 'name' parameter." });
    }
    let rows = []; // Declare rows here
    let records = []; // Also declare records here

    try {
        [rows] = await connection.execute("SELECT id, name, score, created_at FROM extraunary WHERE name = ?", [nameToSearch]);
        
        console.log("Fetched rows:", rows); // Log the rows here, where they are guaranteed to exist

        records = rows.map(row => ({
            id: row.id,
            name: row.name,
            score: row.score,
            created_at: moment(row.created_at).format('YYYY-MM-DD')
        }));
        
        res.json(records); // Move res.json here to ensure it's only called on success
    } catch (error) {
        console.error("Error fetching records by name:", error);
        console.error("Error details:", rows); // Now rows is accessible and will be an empty array
        res.status(500).json({ error: "Internal server error." });
    }
    res.json(records);
}));

app.post('/record', withConnection(async (req, res, connection) => {
    const { name, score, created_at } = req.body;
    if (!name || score === undefined || !created_at) {
        return res.status(400).json({ error: "Invalid JSON body. Required fields: 'name', 'score', 'created_at'." });
    }

    const created_at_dt = moment(created_at, 'DD-MM-YYYY', true);
    if (!created_at_dt.isValid()) {
        return res.status(400).json({ error: "Invalid 'created_at' date format. Please use 'dd-mm-yyyy'." });
    }

    if (isNaN(parseInt(score))) {
        return res.status(400).json({ error: "'score' must be an integer." });
    }

    const [result] = await connection.execute("INSERT INTO extraunary (name, score, created_at) VALUES (?, ?, ?)", [name, parseInt(score), created_at_dt.toDate()]);
    res.status(201).json({ message: "Record added successfully", id: result.insertId });
}));

app.listen(port, () => {
    console.log(`Server is running on port ${port}`);
});