const BASEplate = require('./BASEplate');

class ADCplate extends BASEplate {
    constructor (addr) {
        super(addr, "POWER");
    }
}

module.exports = ADCplate;
