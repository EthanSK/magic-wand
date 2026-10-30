// Join adjacent declarations/statements to fit the saved Puck image; preserve names, evaluation order and callback-discovery markers.
import {minify} from 'terser';
let source='';for await(const chunk of process.stdin)source+=chunk;
const result=await minify(source,{compress:{defaults:false,join_vars:true,sequences:true},mangle:false,format:{comments:false,ascii_only:true}});
if(typeof result.code!=='string')throw Error('Missing compiled device source');
process.stdout.write(result.code);
