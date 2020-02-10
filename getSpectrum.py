import struct
import consts
import sys
# takes a file object set up to read bytes; returns tuple with:
# 0 sector size
# 1 mini sector size
# 2 num SAT sectors
# 3 root directory index
# 4 SSAT start index
# 5 num SSAT sectors
# 6 SAT start index
# 7 ministream start
# 8 ministream size cutoff

def getParams(f):
    # sector size (powers of two)
    f.seek(30, 0)
    sectSize = 1 << struct.unpack('h', f.read(2))[0]

    # mini sector (powers of two)
    miniSectSize = 1 << struct.unpack('h', f.read(2))[0]

    # number of SAT sectors
    f.seek(44, 0)
    numSAT = struct.unpack('i', f.read(4))[0]

    # root directory
    sidRoot = struct.unpack('i', f.read(4))[0]

    # ministream size cutoff
    f.seek(56, 0)
    ministreamCutoff = struct.unpack('i', f.read(4))[0]
    # SSAT index
    sidSSAT = struct.unpack('i', f.read(4))[0]

    # num SSAT sectors
    numSSAT = struct.unpack('i', f.read(4))[0]

    # SAT index
    f.seek(76,0)
    sidSAT = struct.unpack('i', f.read(4))[0]

    # ministream index
    f.seek(consts.HEADERSIZE + sectSize*sidRoot + 116)
    sidMini = struct.unpack('i', f.read(4))[0]
    
    return (sectSize, miniSectSize, numSAT, sidRoot, ministreamCutoff, sidSSAT, numSSAT, sidSAT, sidMini)

def dirIndToOffset(ind, params, f):
    offSet = ind*consts.SUB_SECTOR_SIZE
    sid = params[consts.SID_ROOT_IND];

    sectSize = params[consts.SECT_SIZE_IND]
    SATOffset = params[consts.SID_SAT_IND]*sectSize + consts.HEADERSIZE
    
    while offSet >= sectSize:
       offSet = offSet - sectSize
       f.seek(SATOffset + 4*sid)
       sid = struct.unpack('i', f.read(4))[0]
       if sid == -1:
           print("Error: reached end of the sector chain before desired offset")
           break
    return sid*sectSize + consts.HEADERSIZE + offSet

def streamIndToOffset(ind, params, f):
    sectSize = params[consts.SECT_SIZE_IND]
    SATOffset = params[consts.SID_SAT_IND]*sectSize + consts.HEADERSIZE
    
    sid = params[consts.SID_MINI_IND]
    sidSSAT = params[consts.SID_SSAT_IND]

    offset = ind*params[consts.MINI_SECT_SIZE_IND]

    # follow SAT chain for ministream until desired offset is reached
    while offset >= sectSize:
        offset = offset - sectSize
        f.seek(SATOffset + 4*sid)
        sid = struct.unpack('i', f.read(4))[0]
        if sid == -1:
            print("Error: reached of the sector chain before desired offset")
            break
    return sid*sectSize + consts.HEADERSIZE + offset


def getDirName(ind, params, f):
    offSet = dirIndToOffset(ind, params, f)
    f.seek(offSet + 64)
    length = struct.unpack('h', f.read(2))[0]
    f.seek(offSet)
    return f.read(length).decode('utf-8')

def getDirStream(ind, params, f):
    f.seek(dirIndToOffset(ind, params, f)+116)
    b = f.read(4)
    streamInd = struct.unpack('i',b)[0]
    streamSize = struct.unpack('i', f.read(4))[0]
    return getStreamContents(streamInd, streamSize, params, f)

#1 if str1 greater, 0 if str2 greater
def strComp(str1, str2):
    if len(str1) != len(str2):
        return len(str1) > len(str2)
    return str1 > str2

def dirFromPath(root, namelist, params, f):
    node = root
    for name in namelist[:-1]:
        node = findInTree(name, node, params, f)
        if node == -1:
            print("Path led to empty node :(")
            break
        node = getDirLRC(node, params, f)[2]
        
    return findInTree(namelist[-1], node, params, f)

def findInTree(name, ind, params, f):
    nodeName = getDirName(ind, params, f)
    while nodeName != name:
        L,R,C = getDirLRC(ind, params, f)
        
        if strComp(name, nodeName):
            ind = R
        else:
            ind = L
        if ind == -1:
            break
        nodeName = getDirName(ind, params, f)
    return ind
            
def getDirLRC(ind, params, f):
    offSet = dirIndToOffset(ind, params, f)
    f.seek(offSet + 68)
    leftInd = struct.unpack('i', f.read(4))[0]
    rightInd = struct.unpack('i', f.read(4))[0]
    childInd = struct.unpack('i', f.read(4))[0]
    return (leftInd, rightInd, childInd)

def traverseDirSibs(ind, params, f):
    nodes = []
    queue = [ind]
    while len(queue) > 0:
        node = queue.pop()
        nodes.append(node)
        L, R, C = getDirLRC(node, params, f)
        if L > -1:
            queue.append(L)
        if R > -1:
            queue.append(R)
    return nodes


def printDir(ind, params, f, level):
    for ind in traverseDirSibs(ind, params, f):
        print('\t'*level  + str(ind) + getDirName(ind, params, f))
        child = getDirLRC(ind, params, f)[2]
        if child != -1:
            printDir(child, params, f, level+1)


def getStreamContents(ind, size, params, f):
    data = b''
    sid = ind

    miniSectSize = params[consts.MINI_SECT_SIZE_IND]
    sectSize = params[consts.SECT_SIZE_IND]
    SSATOffset = params[consts.SID_SSAT_IND]*sectSize + consts.HEADERSIZE
    SATOffset = params[consts.SID_SAT_IND]*sectSize + consts.HEADERSIZE

    if size < params[consts.MINISTREAM_CUTOFF_IND]:
    #for i in range(0,20):
        while size > 0:
            if sid < 0:
                print("Error: reached end of ministream before end of data")
                break 
            f.seek(streamIndToOffset(sid, params, f))
            data += f.read(min(miniSectSize, size))
            size = size - miniSectSize
            sid = getNextMiniSect(sid, params, f)
            
    else:
        while size > 0:
            if sid < 0:
                print("Error: reached end of stream before end of data")
                break
            f.seek(sid*sectSize + consts.HEADERSIZE)
            data += f.read(min(sectSize, size))
            size = size - sectSize
            sid = getNextSect(sid, params, f)

    return data    

def bytesToArr(b, fmt):
    n = int(len(b)/struct.calcsize(fmt))
    return struct.unpack(str(n) + fmt, b)

def getNextSect(sid, params, f):
    
    sectSize = params[consts.SECT_SIZE_IND]
    offset = 4*sid
    sidSAT = params[consts.SID_SAT_IND]

    # not taking into account possibility of multiple MSATS,  it probs wont happen and
    # its late and i don't give a shit
    msatInd = 0
    while offset >= sectSize:
        offset = offset - sectSize
        msatInd = msatInd + 1
        
    f.seek(consts.MSAT_OFFSET + 4*msatInd)
    sidSAT = struct.unpack('i', f.read(4))[0]
        
    f.seek(sidSAT*sectSize + consts.HEADERSIZE + offset)
    return struct.unpack('i', f.read(4))[0]


def removeNull(s1):
    s2 = ""
    for i in range(0, len(s1)):
        if s1[i] != '\x00':
            s2 = s2 + s1[i]
    return s2

def getNextMiniSect(ind, params, f):
    sectSize = params[consts.SECT_SIZE_IND]
    sid = params[consts.SID_SSAT_IND]
    SSATOffset = sid*sectSize + consts.HEADERSIZE
    SATOffset = params[consts.SID_SAT_IND]*sectSize + consts.HEADERSIZE

    offset = ind*4

    
    while offset >= sectSize:
        offset = offset - sectSize
        f.seek(SATOffset + sid*4)
        sid = struct.unpack('i', f.read(4))[0]

    f.seek(sid*sectSize + consts.HEADERSIZE + offset)
    return struct.unpack('i', f.read(4))[0]
    

def main(filename):
    f = open(filename,'rb')
    params = getParams(f)
    
    # Root entry
    name00 = b'\x52\x00\x6f\x00\x6f\x00\x74\x00\x20\x00\x45\x00\x6e\x00\x74\x00\x72\x00\x79\x00\x00\x00'.decode('utf-8')

    # Contents
    name01 = b'\x43\x00\x6f\x00\x6e\x00\x74\x00\x65\x00\x6e\x00\x74\x00\x73\x00\x00\x00'.decode('utf-8')

    # DataStorage1
    name05 = b'\x44\x00\x61\x00\x74\x00\x61\x00\x53\x00\x74\x00\x6f\x00\x72\x00\x61\x00\x67\x00\x65\x00\x31\x00\x00\x00'.decode('utf-8')

    # DataSetGroup
    name08 = b'\x44\x00\x61\x00\x74\x00\x61\x00\x53\x00\x65\x00\x74\x00\x47\x00\x72\x00\x6f\x00\x75\x00\x70\x00\x00\x00'.decode('utf-8')

    # DataSetGroupHeaderInfo
    name12 = b'\x44\x00\x61\x00\x74\x00\x61\x00\x53\x00\x65\x00\x74\x00\x47\x00\x72\x00\x6f\x00\x75\x00\x70\x00\x48\x00\x65\x00\x61\x00\x64\x00\x65\x00\x72\x00\x49\x00\x6e\x00\x66\x00\x6f\x00\x00\x00'.decode('utf-8')

    setToDataPath = []

    # DataSpectrumStorage
    setToDataPath.append(b'\x44\x00\x61\x00\x74\x00\x61\x00\x53\x00\x70\x00\x65\x00\x63\x00\x74\x00\x72\x00\x75\x00\x6d\x00\x53\x00\x74\x00\x6f\x00\x72\x00\x61\x00\x67\x00\x65\x00\x00\x00'.decode('utf-8'))

    # Data
    setToDataPath.append(b'\x44\x00\x61\x00\x74\x00\x61\x00\x00\x00'.decode('utf-8'))

    # X Data.1
    nameXData = b'\x58\x00\x20\x00\x44\x00\x61\x00\x74\x00\x61\x00\x2e\x00\x31\x00\x00\x00'.decode('utf-8')
    # Y Data.1
    nameYData = b'\x59\x00\x20\x00\x44\x00\x61\x00\x74\x00\x61\x00\x2e\x00\x31\x00\x00\x00'.decode('utf-8')
                         
    namelist = [name00, name05, name08]

    dataSetGroupDir = dirFromPath(0, namelist, params, f)

    groupDirContents = traverseDirSibs(getDirLRC(dataSetGroupDir, params, f)[2], params, f)
    dataSets = []
    for d in groupDirContents:
        name = getDirName(d, params, f)
        if (name != name12):
            dataSets.append(d)

    for ds in dataSets:
        name = getDirName(ds, params, f)
        dataDir = dirFromPath(ds, [name] + setToDataPath, params, f)

        fout = open(filename[:-4] +'-'+ removeNull(name) + '.csv', 'w')
        #print(getDirName(dataDir, params, f))

        xdata = []
        ydata = []
        
        for child in traverseDirSibs(getDirLRC(dataDir, params, f)[2], params, f):
            childName = getDirName(child, params, f)
            if childName == nameXData:
                xdata = bytesToArr(getDirStream(child, params, f), 'd')
            if childName == nameYData:
                ydata = bytesToArr(getDirStream(child, params, f), 'd')

        for i in range(0, len(xdata)):
            fout.write("{:f}, {:f}\n".format(xdata[i], ydata[i]))


def main2():
    f = open(sys.argv[1],'rb')
    params = getParams(f)
    
    ind = int(sys.argv[2])
    print(bytesToArr(getDirStream(ind, params,f ), 'd'))

#main2()

def dirPrint():
    f = open(sys.argv[1],'rb')
    params = getParams(f)
    
    ind = int(sys.argv[2])
    name = getDirName(ind, params, f)

    nameXData = b'\x58\x00\x20\x00\x44\x00\x61\x00\x74\x00\x61\x00\x2e\x00\x31\x00\x00\x00'.decode('utf-8')
    
    print(name)
    print(getDirLRC(ind, params, f))
    


def printParams():
    for fname in sys.argv[1:]:
        f = open(fname, 'rb')
        params = getParams(f)
        print(fname, params)
        f.close()

