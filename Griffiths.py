import difflib # for fuzzy matching

class GV:
    def __init__(self, order, target, id, county, barony, union, parish, townland, place_name, place_type, town, 
                 tenant_last, tenant_first, landlord_last, landlord_first, page, date, act, sheet, map_reference):
        self.order = str(order)
        self.target = str(target)
        self.id = str(id)
        self.county = str(county)
        self.barony = str(barony)
        self.union = str(union)
        self.parish = str(parish)
        self.townland = str(townland)
        self.place_name = str(place_name)
        self.place_type = str(place_type)
        self.town = str(town)
        self.tenant_last = str(tenant_last)
        self.tenant_first = str(tenant_first)
        self.landlord_last = str(landlord_last)
        self.landlord_first = str(landlord_first)
        self.page = str(page)
        self.date = str(date)
        self.act = str(act)
        self.sheet = str(sheet)
        self.map_reference = str(map_reference)
        self.key1  = (self.tenant_first +self.tenant_last + self.townland).lower()
        self.key = str(tenant_first) + ' ' + str(tenant_last)
        self.key2 = str(landlord_first) + ' ' + str(landlord_last)
    
    def display(self):
        print(self.order, self.target, self.id, self.county, self.barony, self.union, self.parish, self.townland, self.place_name, self.place_type, self.town,
              self.tenant_last, self.tenant_first, self.landlord_last, self.landlord_first, self.page, self.date, self.act, self.sheet, self.map_reference)
    def get_map_ref(self):
        return self.map_reference
    def get_parish(self):
        return self.parish
    
    def get_content(self):
        # Create a list of all attribute values
        return list(vars(self).values())
    

class GVList(list):
    def __init__(self, *args):
        super().__init__(*args)
        self.left_most_idx = 0
        self.right_most_idx = 0

    def add_entries(self, file_name):
    #  todo: check if the list is empty 1st
        ctr = 0
        idxs = ""
        try:
            with open(file_name, 'r', encoding='latin1') as file:
                next(file)  # Skip header
                ctr += 1
                for line in file:
                    ctr += 1
                    parts = line.strip().split(',')
                    if(len(parts) == 20):
                        gv = GV(*parts)
                        self.append(gv)
                    elif(len(parts) != 20):
                        idxs += str(ctr) +"\t" + str(len(parts)) + "\n"
            self.right_most_idx = len(self) - 1 
            # print(f"Total entries added: {ctr}")
        except FileNotFoundError:
            print(f"File not found: {file_name}")
        except UnicodeDecodeError:
            print(f"Encoding error while reading the file: {file_name}")


    def binary_search(self, left, right, key):
        if right >= left:
            mid = left + ((right - left ) // 2)
            if mid < right: # debug this part
                similarity = similarity_rate(str(self[mid].key), key)
                print(f"mid_key: {(self[mid].key)}")
                print(f"Checking index {mid} with similarity {similarity}%")
                if similarity >= 0.9:  
                    self[mid].display()
                    return self[mid]
                elif self[mid].key > key:
                    return self.binary_search(left, mid - 1, key)
                else:
                    return self.binary_search(mid + 1, right, key)
        return -1
    
    def find_entry(self, key):
        # print(f"my_key: {key}")
        entry = self.binary_search(self.left_most_idx, self.right_most_idx, key)
        return entry
    
class GVHash(dict):
    def __init__(self,file_name, **args):
        super().__init__(**args)
        self.add_entries(file_name)

    def add_entries(self, file_name):
        with open(file_name, 'r', encoding='latin1') as inFile:
            next(inFile)  # Skip the header line
            for line in inFile:
                parts = line.strip().split(',')
                if len(parts) == 20:
                    gv = GV(*parts)
                    if gv.key in self.keys():
                        self[gv.key].append(gv)
                    else:
                        self[gv.key] = [gv]
                else:
                    print("Debug if happens")
        print("entries added successfully")
    
    def find_entry(self, key : str) -> list:
        return self.get(key, -1)


def similarity_rate(str1, str2):
    similarity = difflib.SequenceMatcher(None, str1, str2).ratio()
    return round(similarity, 2)


class TownlandEntry:
    def __init__(self, townland) -> None:
        self.townland = townland


class TownlandList(list):
    def __init__self(self):
        super.__init__()
        self.left_most_idx = 0
        self.right_most_idx = 0

    def add_entries(self, file_name):
        self.left_most_idx = 0
        ctr = 0
        idxs = ""
        with open(file_name,'r') as file:
            for townland in file:
                townland_entry = TownlandEntry(townland)
                self.append(townland_entry)
                ctr += 1
            self.right_most_idx = ctr - 1
    
    def binary_search(self, left, right, key):
        if right >= left:
            mid = (left+right) // 2
            similarity = similarity_rate(str(self[mid].townland), key)
            print(f"mid_key: {(self[mid].townland)}")
            print(f"Checking index {mid} with similarity {similarity}%") 
            if similarity >= 0.9:
                return self[mid]
            elif self[mid].townland > key:
                return self.binary_search(left,mid-1,key)
            else:
                return self.binary_search(mid+1, right, key)
        return -1

    def find_townland(self, key):
        return(self.binary_search(self.left_most_idx, self.right_most_idx, key))
    