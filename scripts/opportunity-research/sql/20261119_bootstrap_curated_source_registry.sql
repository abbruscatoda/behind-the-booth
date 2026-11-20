-- Bootstrap the exact 25 source tuples reviewed in discovery.py so
-- publication and lead intake share the same registry from deployment.
insert into btb_private.triangle_research_sources(source_url,organizer,city,active)
values
('https://www.trianglepopup.com/applications','Triangle Pop-Up','Raleigh'),
('https://thenightmarketcompany.com/','Night Market Company','Cary'),
('https://shoplocalraleigh.org/vendor-information/','Shop Local Raleigh','Raleigh'),
('https://www.geekandgrubmarket.com/vendorapplication','Geek and Grub','Raleigh'),
('https://hummingbirdmarketnc.com/member-markets','Hummingbird Market','Raleigh'),
('https://www.caryfarmersmarket.com/vendor-application/','Cary Farmers Market','Cary'),
('https://www.hillsboroughartscouncil.org/last-fridays-markets','Hillsborough Arts Council','Hillsborough'),
('https://www.takethehighstreet.com/thebazaar','The Bazaar','Carrboro'),
('https://blackfarmersmkt.org/the-market/','Black Farmers Market','Durham'),
('https://www.durhamcraftmarket.com/saturdays-in-durham-central-park.html','Durham Craft Market','Durham'),
('https://www.carrborofarmersmarket.com/','Carrboro Farmers Market','Carrboro'),
('https://www.apexfarmersmarket.com/','Apex Farmers Market','Apex'),
('https://www.thechapelhillfarmersmarket.com/','Chapel Hill Farmers Market','Chapel Hill'),
('https://www.hollyspringsnc.gov/319/Farmers-Market','Holly Springs Farmers Market','Holly Springs'),
('https://westernwakefarmersmarket.org/','Western Wake Farmers Market','Morrisville'),
('https://www.enoriverfarmersmarket.com/','Eno River Farmers Market','Hillsborough'),
('https://www.fvgrowersmarket.com/','Fuquay-Varina Growers Market','Fuquay-Varina'),
('https://www.ymcatriangle.org/events/vendor-market','YMCA of the Triangle','Cary'),
('https://artspacenc.org/calls-for-art/','Artspace','Raleigh'),
('https://www.artsplosure.org/first-night-raleigh','Artsplosure','Raleigh'),
('https://wakeforestmarket.org/vendors/become-a-vendor/','Wake Forest Farmers Market','Wake Forest'),
('https://www.chathammillsfarmersmarket.com/vendors/','Chatham Mills Farmers Market','Pittsboro'),
('https://www.garnernc.gov/departments/parks-recreation-and-cultural-resources/events/vendor-interest','Town of Garner','Garner'),
('https://www.knightdalenc.gov/parks-recreation-and-cultural-programs/festivals-and-events/vendor-interest-form','Town of Knightdale','Knightdale'),
('https://www.ncagr.gov/divisions/marketing/farmers-markets-agricultural-centers/state-farmers-market-raleigh/vendor-information','State Farmers Market','Raleigh')
on conflict(source_url) do update set organizer=excluded.organizer,city=excluded.city,active=true,updated_at=now();
