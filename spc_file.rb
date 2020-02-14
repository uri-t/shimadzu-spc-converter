class SpcFile
  HEADER_ENTRIES = {sector_size_exp:       {offset: 30, size: 2},
                    short_sector_size_exp: {offset: 32, size: 2},
                    num_sat_sectors:       {offset: 44, size: 4},
                    root_sid:              {offset: 48, size: 4},
                    stream_size_cutoff:    {offset: 56, size: 4},
                    ssat_sid:              {offset: 60, size: 4},
                    num_ssat_sectors:      {offset: 64, size: 4},
                    msat_sid:              {offset: 68, size: 4},
                    num_msat_sectors:      {offset: 72, size: 4},
                    msat:                  {offset: 76, size: 436}}

  DIRECTORY_ENTRIES = {name:         {offset: 0,   size: 64},
                       name_size:    {offset: 64,  size: 2},
                       type:         {offset: 66,  size: 1},
                       color:        {offset: 67,  size: 1},
                       left_sib_id:  {offset: 68,  size: 4},
                       right_sib_id: {offset: 72,  size: 4},
                       child_id:     {offset: 76,  size: 4},
                       sid:          {offset: 116, size: 4},
                       size:         {offset: 120, size: 4}}
  DIRECTORY_SIZE = 128
  
  def initialize(fname)
    @fname = fname
  end

  def header
    if ! @header
      @header = {}
      HEADER_ENTRIES.keys.each do |k|
        offset = HEADER_ENTRIES[k][:offset]
        size = HEADER_ENTRIES[k][:size]
        unpacker = {2 => 's', 4 => 'l'}[size] || 'l*'
        @header[k] = File.binread(@fname, size, offset).unpack(unpacker)
        if @header[k].size == 1
          @header[k] = @header[k][0]
        end
      end
    end
    @header
  end

  def get_dir(dir_id)
    offset = DIRECTORY_SIZE*dir_id
    directory_stream = stream_list(header[:root_sid])

    sector_offset = offset/(2**header[:sector_size_exp])

    if sector_offset > directory_stream.size
      raise("This directory is outside the allotted space for directories")
    end

    sid = directory_stream[sector_offset]

    offset = offset % 2**header[:sector_size_exp]
    dir_offset = (sid+1)*2**header[:sector_size_exp]+offset

    dir = {}
    unpacker = {1 => 'c', 2 => 's', 4 => 'l'}
    DIRECTORY_ENTRIES.keys.each do |k|
      entry_offset = DIRECTORY_ENTRIES[k][:offset]
      size  = DIRECTORY_ENTRIES[k][:size]
      unpack_str = unpacker[size] || 's'
      dir[k] = File.binread(@fname, size, dir_offset+entry_offset).unpack(unpack_str)[0]
      #dir[k] = File.binread(@fname, size, dir_offset+entry_offset)
    end
    dir[:name] = File.binread(@fname, dir[:name_size], dir_offset).unpack('a*')[0].split("").map {|x| x.ord}.select{|x| x>=32}.map{|x| x.chr}.join
    return dir
  end

  # returns the SAT stream as a list of SIDS
  def sat_sids
    sat_sids = header[:msat].select{|x| x > 0}

    # TODO--add logic to handle when there are multiple MSAT sectors
  end

  def ssat_table()
    ssat_sectors = stream_list(header[:ssat_sid])
  end

  def ssat
    sids_raw = []
    ssat_table.each do |s|
      size = 2**header[:sector_size_exp]
      offset = (s+1)*size
      sids_raw.concat(File.binread(@fname, size, offset).unpack('l*'))
    end
    sids_raw
  end

  def short_stream_list(start_id)
    sids_raw = ssat
    stream = []
    sid = start_id
    while sid > 0
      stream << sid
      sid = sids_raw[sid]
    end
    return stream
  end


  def sat()
    sids_raw = []
    sat_sids.each do |s|
      size = 2**header[:sector_size_exp]
      offset = (s+1)*size
      sids_raw.concat(File.binread(@fname, size, offset).unpack('l*'))
    end
    return sids_raw
  end

  
  def all_streams
    visited = []
    sat.each do |sid|
      if ! visited.include?(sid)
        stream =  stream_list(sid)
        visited.concat(stream)
        if stream.size > 0
          puts stream.to_s
        end
      end
    end
  end
  
    
  # returns list of sector ids in the order in which they appear in the normal stream
  # reads from SAT table
  def stream_list(start_id)
    sids_raw = sat
    stream = []
    sid = start_id
    while sid > 0
      stream << sid
      sid = sids_raw[sid]
    end
    return stream
  end

  def get_stream_data(start_sid)
    data = ""
    sector_size = 2**header[:sector_size_exp]
    
    stream_list(start_sid).each do |sid|
      offset = (sid+1)*sector_size
      data += File.binread(@fname, sector_size, offset)
    end
    return data
  end

  def get_mini_stream_data()
    data = ""

    # sector id of the beginning of the minisector stream is stored in
    # the root directory (sid entry)
    start_sid = get_dir(0)[:sid]

    return get_stream_data(start_sid)
  end


  def read_stream(ind, size)

    if size <= header[:stream_size_cutoff]
      full_stream = get_mini_stream_data.split("")
      
      short_sector_size = 2**header[:short_sector_size_exp]

      out = []
      short_stream_list(ind).each do |ssid|
        out.concat(full_stream[short_sector_size*ssid, short_sector_size])
      end
      return out
    else
      full_stream = get_stream_data(ind)
      return full_stream[0, size]
    end
  end

  def dir_tree
    root = get_dir(0)
    add_children(root)
    return root
  end

  def add_children(dir)
    if dir[:child_id] > 0
      child = get_dir(dir[:child_id])
      dir[:children] = get_siblings(child)
      dir[:children].each do |x|
        add_children(x)
      end
    end
  end

  def get_siblings(dir)
    sib_ids = [dir[:left_sib_id], dir[:right_sib_id]].select {|x| x > 0}

    immediate_sibs = sib_ids.map{|x| get_dir(x)}

    sibs = []
    immediate_sibs.each do |sib|
      sibs.concat(get_siblings(sib))
    end

    sibs.concat(immediate_sibs)
  end

  def print_tree
    print_node(dir_tree, 0)
  end
  
  def print_node(node, level)
    if level > 1
      return
    end
    puts "  "*level + node[:name]

    (node[:children] || []).each do |c|
      print_node(c, level+1)
    end
  end
end
