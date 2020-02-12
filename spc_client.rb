require_relative 'spc_file.rb'

spc = SpcFile.new('tests/09.spc')

puts spc.header
puts spc.get_dir(0)
puts spc.get_dir(1)
puts spc.get_dir(38)

#puts spc.stream_list(66)
puts spc.read_stream(66, 9608).unpack('d*').to_s
