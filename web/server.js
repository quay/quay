var http = require('http');

var nStatic = require('node-static');

var fileServer = new nStatic.Server('./dist');

http.createServer(function (request, response) {
    request.addListener('end', function () {
        fileServer.serve(request, response, function (err, result) {
            if (err) { // There was an error serving the file
                console.error("Error serving " + request.url + " - " + err.message);

                if (err.status === 404) { // If the file wasn't found, serve index.html
                    console.error("serving index.html instead");
                    fileServer.serveFile('index.html', 200, {}, request, response);
                    return;
                }


                // Respond to the client
                response.writeHead(err.status, err.headers);
                response.end();
            } else {
                console.info(`[${new Date().toISOString()}] ${request.method} ${request.url} ${response.statusCode} `);
            }
        });
    }).resume();
}).listen(9000);
