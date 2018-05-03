import re
import wordninja


def multiple_replace(text, adict):
    rx = re.compile('|'.join(map(re.escape, adict)))

    def one_xlat(match):
        return adict[match.group(0)]
    return rx.sub(one_xlat, text)


def repair_column_series_census_metadata(table_number, column_name, column_heading):
    column_number = int(column_name[1:])

    if table_number.startswith("t"):
        column_heading = multiple_replace(column_heading, {
            "2006Census:Males": "2006 Census: Males",
            "2006Census:Females": "2006 Census: Females",
            "2006Census:Persons": "2006 Census: Persons",
            "2006Census": "2006 Census",
            "2011Census:Males": "2011 Census: Males",
            "2011Census:Females": "2011 Census: Females",
            "2011Census:Persons": "2011 Census: Persons",
            "2011Census": "2011 Census",
            "2016Census:Males": "2016 Census: Males",
            "2016Census:Females": "2016 Census: Females",
            "2016Census:Persons": "2016 Census: Persons",
            "2016Census": "2016 Census",
        })

        if table_number == "t12":
            # These are mislabelled as part of the 2006 Census series
            if column_number >= 4949 and column_number <= 4968:
                column_heading = column_heading.replace("2006 Census", "2011 Census")
            # These are mislabelled as part of the 2011 Census series
            elif column_number >= 5259 and column_number <= 5278:
                column_heading = column_heading.replace("2011 Census", "2016 Census")
        elif table_number == "t20":
            # These are mislabelled as part of the 2006 Census series
            if column_number >= 8326 and column_number <= 8337:
                column_heading = column_heading.replace("2006 Census", "2011 Census")

    return column_heading


def repair_series_name(table_number, column_name, metadata, seriesName):
    """
    Handle tables where the series name (part of the column heading metadata) 
    has been typoed or incorrectly coded.

    IMPORTANT: Any changes here also need to be done in repair_census_metadata() and repair_column_series_census_metadata()
    @FIXME For 2021 we should probably refactor these functions so we don't violate DRY. (Assuming we're still reduced to parsing XLS files to get metadata)
    """
    if seriesName is not None:
        oldSeriesName = seriesName

        # The TSP DataPack contains a pile of typos where words are run together without spaces *sigh*
        if table_number.startswith("t"):
            seriesName = multiple_replace(seriesName, {
                "2006CENSUS-MALES": "2006 Census: Males",
                "2006CENSUS-FEMALES": "2006 Census: Females",
                "2006CENSUS-PERSONS": "2006 Census: Persons",
                "2006CENSUS": "2006 Census",
                "2011CENSUS-MALES": "2011 Census: Males",
                "2011CENSUS-FEMALES": "2011 Census: Females",
                "2011CENSUS-PERSONS": "2011 Census: Persons",
                "2011CENSUS": "2011 Census",
                "2016CENSUS-MALES": "2016 Census: Males",
                "2016CENSUS-FEMALES": "2016 Census: Females",
                "2016CENSUS-PERSONS": "2016 Census: Persons",
                "2016CENSUS": "2016 Census",
            })

        elif table_number == "w03":
            seriesName = seriesName.replace("EmployeeS", "Employee")
        elif table_number == "w19":
            seriesName = seriesName.replace(" STUDENTS", " STUDENT")

        elif table_number.startswith("i"):
            seriesName = seriesName.replace("HOUSEHOLDS WITH INDIGENOUS PERSON(S)", "Households with Aboriginal and or Torres Strait Islander Persons")
    return seriesName


def fixLackOfSpaces(table_number, column_name, metadata, seriesName):
    """
    The TSP datapack for 2016 had an issue with its column names. They were lacking spaces between words!
    So we have to turn "Employed:Workedfull-time|2016CENSUS-PERSONS" into "Employed Worked full time|2016CENSUS-PERSONS"
    """
    def getKindWithoutSeriesName(kind, seriesName):
        if seriesName is not None:
            return kind.split("|")[0]
        return kind

    def getTypeWithoutSeriesName(type, seriesName):
        if seriesName is not None:
            seriesName = seriesName.replace(":", "")
            return re.sub(seriesName, "", type, re.IGNORECASE).strip()
        return type

    # The TSP DataPack contains a pile of typos where words are run together without spaces *sigh*
    if table_number.startswith("t"):
        # No need to repair Total columns
        if metadata["kind"].startswith("Total|"):
            return metadata

        # No need to repair T34 and T35
        if metadata["kind"].startswith("2006 Census:") or metadata["kind"].startswith("2011 Census:") or metadata["kind"].startswith("2016 Census:"):
            return metadata

        kindWithoutSeries = getKindWithoutSeriesName(metadata["kind"], seriesName)

        # Wordninja doesn't handle currencies and number ranges well (they split as individual characters).
        # So we handle this by eplacing them with a special nonsense word "hotcakes" prior to running wordninja.

        # Just in case they use our special nonsense word was used in a column.
        if "hotcake" in kindWithoutSeries:
            raise Exception("Hotcakes!")

        kindWithoutSeriesAndSpecial = kindWithoutSeries

        match = re.search("(?P<currencyornumberrange>\$?[0-9]{1,}(-\$?[0-9]{1,})?)", kindWithoutSeries)
        if match is not None:
            kindWithoutSeriesAndSpecial = kindWithoutSeries.replace(match.group("currencyornumberrange"), "hotcake")

        newKindWithSpaces = " ".join(wordninja.split(kindWithoutSeriesAndSpecial.lower()))
        if match is not None:
            newKindWithSpaces = newKindWithSpaces.replace("hotcake", match.group("currencyornumberrange"))
        newKindWithSpaces = newKindWithSpaces.capitalize()
        metadata["kind"] = metadata["kind"].replace(kindWithoutSeries, newKindWithSpaces)

        if table_number == "t11":
            metadata["kind"] = metadata["kind"].replace("very well orwell", "very well or well")

        return metadata

    return metadata


def repair_census_metadata_first_pass(table_number, column_name, metadata):
    """
    Used to repair issues with column headings. Repeats some of what repair_column_series_census_metadata()
    and repair_series_name() do, but it used in different parts of attrs.py.

    @FIXME For 2021 if we're still using this code.
    """
    column_number = int(column_name[1:])

    if table_number == "t12":
        # These are mislabelled as part of the 2006 Census series
        if column_number >= 4949 and column_number <= 4968:
            metadata["kind"] = metadata["kind"].replace("2006CENSUS", "2011CENSUS")
        # These are mislabelled as part of the 2011 Census series
        elif column_number >= 5259 and column_number <= 5278:
            metadata["kind"] = metadata["kind"].replace("2011CENSUS", "2016CENSUS")
    elif table_number == "t20":
        # These are mislabelled as part of the 2006 Census series
        if column_number >= 8326 and column_number <= 8337:
            metadata["kind"] = metadata["kind"].replace("2006CENSUS", "2011CENSUS")
    return metadata


def repair_census_metadata(table_number, column_name, metadata, seriesName):
    metadata["type"] = metadata["type"].strip().replace("_", " ").replace("-", " ")
    metadata["kind"] = repair_column_series_census_metadata(table_number, column_name, metadata["kind"])
    metadata = fixLackOfSpaces(table_number, column_name, metadata, seriesName)

    if table_number == "g11":
        metadata["kind"] = metadata["kind"].replace("2006 2015", "2006 2010")
        metadata["kind"] = metadata["kind"].replace("2006-2015", "2006 2010")
    elif table_number == "g18":
        metadata["kind"] = metadata["kind"].replace("No need for assistance", "Does not have need for assistance")
    elif table_number == "g24":
        metadata["kind"] = multiple_replace(metadata["kind"], {
            ": 1": " One child",
            ": 2": " Two children",
            ": 3": " Three children",
            ": 4": " Four children",
            ": 5": " Five children",
            ": 6 or more": " Six or more children",
            ": None": " No children",
        })
    elif table_number == "g38":
        # metadata["type"] = metadata["type"].replace("Sixor more", "Six or more")
        metadata["kind"] = metadata["kind"].replace("Six bedrooms or more", "Six or more bedrooms")
    elif table_number == "g52":
        metadata["kind"] = metadata["kind"].replace("49 and over", "49 hours and over")
    elif table_number == "g56":
        metadata["kind"] = metadata["kind"].replace("Unemployed, looking for work: ", "Unemployed looking for ")
    elif table_number == "g58":
        metadata["kind"] = metadata["kind"].replace("49 and over", "49 hours and over")

    elif table_number == "p10":
        metadata["kind"] = metadata["kind"].replace("1966-1965", "1956-1965")
        metadata["kind"] = metadata["kind"].replace("Year of arrival: Year of arrival not stated", "Year of arrival not stated")
    elif table_number == "p18":
        metadata["kind"] = metadata["kind"].replace("Overseas vistors", "Overseas visitors")
    elif table_number == "p19":
        metadata["kind"] = metadata["kind"].replace("Overseas vistors", "Overseas visitors")
    elif table_number == "p20":
        # Remove duplicate prefix
        if column_name == "p4001":
            metadata["kind"] = metadata["kind"].replace("Unpaid domestic work: number of hours: Unpaid domestic work: number of hours:", "Unpaid domestic work: number of hours:")
    elif table_number == "p21":
        # Remove duplicate prefix
        if column_name == "p4229":
            metadata["kind"] = metadata["kind"].replace("Unpaid assistance to a person with a disability: Unpaid assistance to a person with a disability:", "Unpaid assistance to a person with a disability:")
    elif table_number == "p24":
        metadata["kind"] = multiple_replace(metadata["kind"], {
            ": 1": " One child",
            ": 2": " Two children",
            ": 3": " Three children",
            ": 4": " Four children",
            ": 5": " Five children",
            ": 6 or more": " Six or more children",
            ": None": " No children",
        })

    elif table_number == "t07":
        metadata["kind"] = multiple_replace(metadata["kind"], {
            "1|": "One child|",
            "2|": "Two|",
            "3|": "Three|",
            "4|": "Four|",
            "5|": "Five|",
            "6 or more|": "Six or more|",
            "none|": "No children|",
        })
    elif table_number == "t15":
        metadata["kind"] = multiple_replace(metadata["kind"], {
            "1|": "One|",
            "2|": "Two|",
            "3|": "Three|",
            "4|": "Four|",
            "5|": "Five|",
            "6 or more|": "Six or more|",
        })
    elif table_number == "t16":
        metadata["kind"] = multiple_replace(metadata["kind"], {
            "1|": "One|",
            "2|": "Two|",
            "3|": "Three|",
            "4|": "Four|",
            "5|": "Five|",
            "6 or more|": "Six or more|",
        })
        metadata["kind"] = metadata["kind"].replace("usually resident", "usually resident in family households")
    elif table_number == "t17":
        metadata["kind"] = multiple_replace(metadata["kind"], {
            "1|": "One|",
            "2|": "Two|",
            "3|": "Three|",
            "4|": "Four|",
            "5|": "Five|",
            "6 or more|": "Six or more|",
        })
        metadata["kind"] = metadata["kind"].replace("usually resident", "usually resident in group households")
    elif table_number == "t18":
        column_number = int(column_name[1:])
        if column_number == 7801:
            # Typoed as "itecture"
            metadata["kind"] = metadata["kind"] = "Dwelling structure Other dwelling"
    elif table_number == "t22" or table_number == "t23":
        metadata["kind"] = multiple_replace(metadata["kind"], {
            "1 child|": "One child|",
            "2 children|": "Two children|",
            "3 children|": "Three children|",
            "4 or more children|": "Four or more children|",
        })
    elif table_number == "t24":
        column_number = int(column_name[1:])
        if column_number == 9686:
            metadata["type"] = metadata["type"].replace("150 149", "150 199")
        elif column_number == 9700:
            metadata["type"] = metadata["type"].replace("150 224", "200 224")
    elif table_number == "t27":
        metadata["kind"] = multiple_replace(metadata["kind"], {
            "1|": "One|",
            "2|": "Two|",
            "3|": "Three|",
            "4 or more|": "Four or more|",
        })
    elif table_number == "t28":
        metadata["type"] = metadata["type"].replace("Has need assistance", "Has need for assistance")

    elif table_number == "w02" or table_number == "w04" or table_number == "w05" or table_number == "w06":
        metadata["kind"] = metadata["kind"].replace("Employees", "Employee")

    elif table_number == "w03":
        metadata["kind"] = metadata["kind"].replace("EmployeeS", "Employee")
    elif table_number == "w12":
        metadata["kind"] = metadata["kind"].replace("Occupation inadequately", "inadequately")
    elif table_number == "w19":
        metadata["kind"] = metadata["kind"].replace(" STUDENTS", " STUDENT")
    elif table_number == "w23":
        metadata["kind"] = metadata["kind"].replace("Institutions:", "Institution:")

    elif table_number == "i01":
        column_number = int(column_name[1:])

        if column_number == 3:
            metadata["kind"] = metadata["kind"].replace("Islander Persons:", "Islander Persons")
        elif column_number >= 52 and column_number <= 54:
            metadata["kind"] = metadata["kind"].replace("Non-Indigenous:", "Non Aboriginal and or Torres Strait Islander:")
        elif column_number == 241:
            metadata["type"] += " Males"
    elif table_number == "i02":
        column_number = int(column_name[1:])

        # Columns mistakenly include the row
        if column_number >= 514 and column_number <= 516:
            metadata["kind"] = metadata["kind"].replace("Indigenous: ", "")
        if column_number >= 517 and column_number <= 519:
            metadata["kind"] = metadata["kind"].replace("Non-Indigenous ", "")
        if column_number >= 520 and column_number <= 522:
            metadata["kind"] = metadata["kind"].replace("Indigenous status not stated: ", "")
        if column_number >= 523 and column_number <= 525:
            metadata["kind"] = metadata["kind"].replace("Total ", "")
    elif table_number == "i06":
        if "Non-Indigenous" not in metadata["kind"] and "Indigenous status not stated" not in metadata["kind"]:
            metadata["kind"] = metadata["kind"].replace("Indigenous", "Aboriginal and or Torres Strait Islander")
    elif table_number == "i08":
        metadata["kind"] = metadata["kind"].replace("No need for assistance", "Does not have need for assistance")
    elif table_number == "i10":
        column_number = int(column_name[1:])

        if column_number >= 1624 and column_number <= 1944 and column_name[-1] == "4":
            metadata["kind"] = metadata["kind"].replace("Other dwelling: Caravan\ cabin\ houseboat|", "Other dwelling: Caravan|")
            metadata["kind"] = metadata["kind"].replace("Other dwelling: Cabin\ houseboat|", "Other dwelling: Caravan|")
        elif column_number >= 1645 and column_number <= 1945 and column_name[-1] == "5":
            metadata["kind"] = metadata["kind"].replace("Other dwelling: Caravan\ cabin\ houseboat|", "Other dwelling: Cabin\ houseboat|")

        metadata["kind"] = metadata["kind"].replace("Flat\ unit or apartment", "Dwelling structure Flat unit or apartment")
        metadata["type"] = metadata["type"].replace("Dwelling structure Flat or apartment", "Dwelling structure Flat unit or apartment")
    elif table_number == "i11":
        metadata["kind"] = metadata["kind"].replace("Indigenous households", "Households with Aboriginal and or Torres Strait Islander Persons")
    elif table_number == "i12":
        metadata["kind"] = multiple_replace(metadata["kind"], {
            ": 1": " One",
            ": 2": " Two",
            ": 3": " Three",
            ": 4": " Four",
            ": 5": " Five",
            ": 6 or more": " Six or more",
        })
    elif table_number == "i13":
        metadata["kind"] = metadata["kind"].replace("Households with Indigenous person(s)", "Households with Aboriginal and or Torres Strait Islander Persons")
    elif table_number == "i15":
        column_number = int(column_name[1:])

        # Column heading mislabelled as "Certificate Level nfd|FEMALES"
        if column_number == 2688:
            metadata["kind"] = "Level of education not stated|FEMALES"
        if column_number == 2893:
            metadata["type"] = metadata["type"].replace("Certificatel", "Certificate")

    return metadata