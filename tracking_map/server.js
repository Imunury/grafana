var express = require('express');
var pg = require('pg');
var cors = require('cors');

var app = express();

app.use(cors());

var pool = new pg.Pool({
    user: 'eco0',
    host: 'localhost',
    database: 'chilseo_1',
    password: '820429ape',
    port: 5432,
});

app.get('/api/gps', function (req, res) {
    pool.query('SELECT lat, lon FROM gps_data', (error, results) => {
        if (error) {
            throw error;
        }
        res.status(200).json(results.rows);
    });
});

app.listen(3002, function () {
    console.log('Server is running on port 3002');
});
