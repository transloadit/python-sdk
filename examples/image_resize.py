from transloadit.client import Transloadit

client = Transloadit("TRANSLOADIT_KEY", "TRANSLOADIT_SECRET")
assembly = client.new_assembly()
assembly.add_file(open("fixtures/lol_cat.jpg", "rb"))
assembly.add_step("resize", "/image/resize", {"width": 70, "height": 70})
response = assembly.create(wait=True)

result_url = response.data.get("results").get("resize")[0].get("ssl_url")
print("Your result:", result_url)
