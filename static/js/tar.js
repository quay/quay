/**
 * Tar library code based on the tar-async project (MIT License):
 * https://github.com/beatgammit/tar-async
 */
// Production steps of ECMA-262, Edition 5, 15.4.4.18
// Reference: http://es5.github.com/#x15.4.4.18
if (!Array.prototype.forEach) {
    Array.prototype.forEach = function(callback, thisArg) {
        var T, k;

        if (this == null) {
            throw new TypeError(" this is null or not defined");
        }

        // 1. Let O be the result of calling ToObject passing the |this| value as the argument.
        var O = Object(this);

        // 2. Let lenValue be the result of calling the Get internal method of O with the argument "length".
        // 3. Let len be ToUint32(lenValue).
        var len = O.length >>> 0;

        // 4. If IsCallable(callback) is false, throw a TypeError exception.
        // See: http://es5.github.com/#x9.11
        if (typeof callback !== "function") {
            throw new TypeError(callback + " is not a function");
        }

        // 5. If thisArg was supplied, let T be thisArg; else let T be undefined.
        if (arguments.length > 1) {
            T = thisArg;
        }

        // 6. Let k be 0
        k = 0;

        // 7. Repeat, while k < len
        while (k < len) {

            var kValue;

            // a. Let Pk be ToString(k).
            //   This is implicit for LHS operands of the in operator
            // b. Let kPresent be the result of calling the HasProperty internal method of O with argument Pk.
            //   This step can be combined with c
            // c. If kPresent is true, then
            if (k in O) {

                // i. Let kValue be the result of calling the Get internal method of O with argument Pk.
                kValue = O[k];

                // ii. Call the Call internal method of callback with T as the this value and
                // argument list containing kValue, k, and O.
                callback.call(T, kValue, k, O);
            }
            // d. Increase k by 1.
            k++;
        }
        // 8. return undefined
    };
}


// Polyfill: https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Array/some
if (!Array.prototype.some) {
    Array.prototype.some = function(fun /*, thisArg */ ) {
        'use strict';

        if (this === void 0 || this === null)
            throw new TypeError();

        var t = Object(this);
        var len = t.length >>> 0;
        if (typeof fun !== 'function')
            throw new TypeError();

        var thisArg = arguments.length >= 2 ? arguments[1] : void 0;
        for (var i = 0; i < len; i++) {
            if (i in t && fun.call(thisArg, t[i], i, t))
                return true;
        }

        return false;
    };
}


(function() {

    function pad(num, bytes, base) {
        num = num.toString(base || 8);
        return "000000000000".substr(num.length + 12 - bytes) + num;
    }

    /*
    struct posix_header {             // byte offset
      char name[100];               //   0
      char mode[8];                 // 100
      char uid[8];                  // 108
      char gid[8];                  // 116
      char size[12];                // 124
      char mtime[12];               // 136
      char chksum[8];               // 148
      char typeflag;                // 156
      char linkname[100];           // 157
      char magic[6];                // 257
      char version[2];              // 263
      char uname[32];               // 265
      char gname[32];               // 297
      char devmajor[8];             // 329
      char devminor[8];             // 337
      char prefix[155];             // 345
    // 500
    };
  */

    var headerFormat = [{
        'field': 'filename',
        'length': 100,
        'type': 'string'
    }, {
        'field': 'mode',
        'length': 8,
        'type': 'number'
    }, {
        'field': 'uid',
        'length': 8,
        'type': 'number'
    }, {
        'field': 'gid',
        'length': 8,
        'type': 'number'
    }, {
        'field': 'size',
        'length': 12,
        'type': 'number'
    }, {
        'field': 'mtime',
        'length': 12,
        'type': 'number'
    }, {
        'field': 'checksum',
        'length': 8,
        'type': 'number'
    }, {
        'field': 'type',
        'length': 1,
        'type': 'number'
    }, {
        'field': 'linkName',
        'length': 100,
        'type': 'string'
    }, {
        'field': 'ustar',
        'length': 8,
        'type': 'string'
    }, {
        'field': 'owner',
        'length': 32,
        'type': 'string'
    }, {
        'field': 'group',
        'length': 32,
        'type': 'string'
    }, {
        'field': 'majorNumber',
        'length': 8,
        'type': 'number'
    }, {
        'field': 'minorNumber',
        'length': 8,
        'type': 'number'
    }, {
        'field': 'filenamePrefix',
        'length': 155,
        'type': 'string'
    }, {
        'field': 'padding',
        'length': 12
    }];

    function clean(length) {
        return new Uint8Array(length);
    }

    function formatHeader(data) {
        var buffer = new Uint8Array(5000);
        offset = 0;

        headerFormat.forEach(function(value) {
            var v = data[value.field] || "";
            for (var i = 0; i < v.length; ++i) {
                buffer[offset + i] = v.charCodeAt(i);
            }
            offset += value.length;
        });

        return buffer.slice(0, offset);
    }

    var totalRead = 0,
        recordSize = 512,
        fileBuffer,
        leftToRead,
        fileTypes = [
            'normal', 'hard-link', 'symbolic-link', 'character-special', 'block-special', 'directory', 'fifo', 'contiguous-file'
        ];

    function filterDecoder(input) {
        var filter = [];
        if (!input) {
            return [0, 7];
        }

        if (typeof input === 'string') {
            input = [].push(input);
        }

        if (!(input instanceof Array)) {
            console.error('Invalid fileType. Only Arrays or strings are accepted');
            return;
        }

        input.forEach(function(i) {
            var index = fileTypes.indexOf(i);
            if (index < 0) {
                console.error('Filetype not valid. Ignoring input:', i);
                return;
            }

            filter.push(i);
        });

        return filter;
    }

    function readInt(value) {
        return parseInt(value.replace(/^0*/, ''), 8) || 0;
    }

    function readString(buf) {
        var str = '';
        for (var i = 0; i < buf.length; ++i) {
            if (buf[i] == 0) {
                break;
            }
            str += String.fromCharCode(buf[i]);
        }
        return str;
    }

    function doHeader(buf, cb) {
        var data = {},
            offset = 0,
            checksum = 0;

        function updateChecksum(value) {
            var i, length;

            for (i = 0, length = value.length; i < length; i += 1) {
                checksum += value.charCodeAt(i);
            }
        }

        headerFormat.some(function(field) {
            var tBuf = buf.subarray(offset, offset + field.length),
                tString = String.fromCharCode.apply(null, tBuf);

            offset += field.length;

            if (field.field === 'ustar' && !/ustar/.test(tString)) {
                // end the loop if not using the extended header
                return true;
            } else if (field.field === 'checksum') {
                updateChecksum('        ');
            } else {
                updateChecksum(tString);
            }

            if (field.type === 'string') {
                data[field.field] = readString(tBuf);
            } else if (field.type === 'number') {
                data[field.field] = readInt(tString);
            }
        });

        if (checksum !== data.checksum) {
            cb.call(this, 'Checksum not equal', checksum, data.checksum);
            return false;
        }

        cb.call(this, null, data, recordSize);
        return true;
    }

    function readTarFile(state, data) {
        var fileBuffer = new Uint8Array(data.size);
        fileBuffer.set(state.buffer.subarray(0, data.size));
        state.files.push({
            'meta': data,
            'buffer': fileBuffer
        });
    }

    function removeTrailingNulls(state) {
        // If we're not an even multiple, account for trailing nulls
        if (state.totalRead % recordSize) {
            var bytesBuffer = recordSize - (state.totalRead % recordSize);

            // If we don't have enough bytes to account for the nulls
            if (state.buffer.length < bytesBuffer) {
                state.totalRead += bytesBuffer;
                return;
            }

            // Throw away trailing nulls
            state.buffer = state.buffer.subarray(bytesBuffer);
            state.totalRead += bytesBuffer;
        }
    }

    function processTar(state) {
        if (state.totalRead == 0) {
            // Remove trailing nulls.
            removeTrailingNulls(state);
        }

        // Check to see if/when we are done.
        if (state.buffer.length < recordSize) {
            state.cb('done', state.totalRead, state.files, null);
            return;
        }

        state.cb('working', state.totalRead, state.files, null);

        doHeader.call(this, state.buffer, function(err, data, rOffset) {
            if (err) {
                if (rOffset === 0) {
                    state.cb('done', state.totalRead, state.files, null);
                    return;
                }
                return state.cb('error', state.totalRead, state.files, err);
            }

            // Update total; rOffset should always be 512
            state.totalRead += rOffset;
            state.buffer = state.buffer.subarray(rOffset);

            // Read the tar file contents.
            readTarFile(state, data);

            // Update the total and offset.
            state.totalRead += data.size;
            state.buffer = state.buffer.subarray(data.size);

            // Remove trailing nulls.
            removeTrailingNulls(state);

            if (state.buffer.length > 0) {
                setTimeout(function() {
                    processTar(state);
                }, 0);
            } else {
                state.cb('done', state.totalRead, state.files, null);
            }
        });
    }

    /*
     * Extract data from an input.
     *
     * @param data The data, in Uint8Array form.
     */
    function Untar(data) {
        this.data = data;
    }

    Untar.prototype.process = function(cb, opt_filter) {
        return processTar({
            'cb': cb,
            'buffer': this.data,
            'fileTypes': filterDecoder(opt_filter || []),
            'totalRead': 0,
            'files': []
        });
    };

    window.Untar = Untar;

    function appendArrays(arr1, arr2) {
      var tmp = new Uint8Array(arr1.length + arr2.length);
      tmp.set(arr1);
      tmp.set(arr2, arr1.length);
      return tmp;
    }

    function Tar() {
        this.data = new Uint8Array(0);
    }

    Tar.prototype.getData = function() {
        return this.data;
    };

    Tar.prototype.emit = function(data) {
        if (typeof data == 'string') {
            var buf = new Uint8Array(data.length);
            for (var i = 0; i < data.length; ++i) {
                buf[i] = data.charCodeAt(i);
            }

            data = buf;
        }

        this.data = appendArrays(this.data, data);
    };

    Tar.prototype.createHeader = function(data) {
        var checksum,
            i,
            length,
            headerBuf;

        // format the header without the checksum
        headerBuf = formatHeader(data);

        // calculate the checksum
        checksum = 0;
        for (i = 0, length = headerBuf.length; i < length; i += 1) {
            checksum += headerBuf[i];
        }

        // pad the checksum
        checksum = checksum.toString(8);
        while (checksum.length < 6) {
            checksum = '0' + checksum;
        }

        // write the checksum into the header
        for (i = 0, length = 6; i < length; i += 1) {
            headerBuf[i + 148] = checksum.charCodeAt(i);
        }

        headerBuf[154] = 0;
        headerBuf[155] = 0x20;
        return headerBuf;
    };

    Tar.prototype.writeData = function(header, input, size) {
        var extraBytes,
            tape = this;

        // and write it out to the stream
        this.emit(header);
        this.written += header.length;

        this.emit(input);
        this.written += input.length;

        extraBytes = recordSize - (size % recordSize || recordSize);
        this.emit(clean(extraBytes));
        this.written += extraBytes;
    };

    Tar.prototype.append = function(filepath, input, opts) {
        var data,
            mode,
            mtime,
            uid,
            gid,
            size,
            tape = this;

        opts = opts || {};
        mode = typeof opts.mode === 'number' ? opts.mode : parseInt('777', 8) & 0xfff;
        mtime = typeof opts.mtime === 'number' ? opts.mtime : parseInt(+new Date() / 1000);
        uid = typeof opts.uid === 'number' ? opts.uid : 0;
        gid = typeof opts.gid === 'number' ? opts.gid : 0;
        size = typeof opts.size === 'number' ? opts.size : input.length;

        data = {
            filename: filepath,
            mode: pad(mode, 7),
            uid: pad(uid, 7),
            gid: pad(gid, 7),
            size: pad(size, 11),
            mtime: pad(mtime, 11),
            checksum: '        ',
            type: '0', // just a file
            ustar: 'ustar ',
            owner: '',
            group: ''
        };

        this.writeData(this.createHeader(data), input, size);
    };

    window.Tar = Tar;

})();