const TINKERplate = require('../TINKERplate');

TINK0 = new TINKERplate(0);

const obj = {args: {}};
let i = 1;
setInterval( () => {
    if (i > 7)
        i = 1;
    obj.cmd = "toggleDOUTbit"
    obj.args.bit = i;
    TINK0.send(obj, (reply) => {});
    i += 1;
}, 500);
