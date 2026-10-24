// Pinned Terser only removes syntax whitespace/comments: names and behavior stay intact.
import {minify} from 'terser';
let source='';for await(const chunk of process.stdin)source+=chunk;
const result=await minify(source,{compress:false,mangle:false,format:{comments:false,ascii_only:true}});
if(typeof result.code!=='string')throw Error('Missing compiled device source');
process.stdout.write(result.code);
