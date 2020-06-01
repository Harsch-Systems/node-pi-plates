const TINKERplate = require('../TINKERplate');

TINK0 = new TINKERplate(0);

let i = 1;
obj = {cmd: "relayTOGGLE", args: {relay: i}};
setTimeout( () => {
    setInterval( () => {
        if (i > 2)
            i = 1;
        obj.args.relay = i
        TINK0.send(obj, (reply) => {});
        i += 1
    }, 500);
}, 1000);


