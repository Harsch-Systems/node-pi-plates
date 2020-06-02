const THERMOplate = require('../THERMOplate');

TP0 = new THERMOplate(0);

TP0.send({cmd: "VERIFY", args: {}}, (reply) => {
    console.log('verified: ' + reply.state);
});
