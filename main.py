from typing import *
import mysql.connector
import prompt_toolkit as pt
import datetime
import traceback

profile = {}
cur = {}

def handler(v):
    pt.application.get_app().exit(result = v)

def getProfile(id):
    cursor = connection.cursor()
    cursor.execute("select id, name, password, address from student where student.id = %s", (id, ))
    values = cursor.fetchall()
    cursor.close()
    return {
        "id": values[0][0],
        "name": values[0][1],
        "password": values[0][2],
        "address": values[0][3],
    }

def main():
    showLoginView()

# login view
def showLoginView():
    while True:
        id = pt.shortcuts.input_dialog(
            title="NU Login",
            text="Student ID",
            cancel_text="Quit"
        )
        if id == None: # user pressed quit
            exit()

        password = pt.shortcuts.input_dialog(
            title="NU Login",
            text="Password",
            password=True
        )
        if password == None: # user pressed cancel
            continue
        # id = "3213"
        # password = "lunch"

        cursor = connection.cursor()
        cursor.execute("select id, name, password, address from student where student.id = %s and student.password = %s", (id, password))
        values = cursor.fetchall()
        cursor.close()

        if len(values) == 0 or str(values[0][0]) != id or values[0][2] != password:
            pt.shortcuts.message_dialog(
                title="NU Login Error",
                text="Wrong student ID or password.\nTake care of CASE SENSITIVE!",
                style=pt.styles.Style.from_dict({
                    "dialog": "bg:#ff0000",
                }),
            )
            continue
        else:
            profile["id"] = values[0][0]
            profile["username"] = values[0][1]
            profile["password"] = values[0][2]
            profile["address"] = values[0][3]
            showStudentMenu() # enter student menu

# student menu
def showStudentMenu():
    while True:
        today = datetime.date.today()
        cur["year"] = today.year
        cur["month"] = today.month
        cur["day"] = today.day
        cur["semester"] = "Q1" if 1 <= today.month <= 6 else "Q2" # [January, June] -> Q1, [July, December] -> Q2

        cursor = connection.cursor()
        cursor.execute("""
            select distinct uosCode, semester, year, grade
            from transcript
            where studId = %s and year = %s
            and semester = %s
        """, (profile["id"], cur['year'], cur['semester']))
        values = cursor.fetchall()
        cursor.close()

        # build gui
        courses = list(map(lambda v: (
            v[0], # course id
            "   ".join([
                v[0], # course id
                v[1], # semester
                str(v[2]), # year
                str(v[3] or "N/A"), # grade
            ]),
        ), values))

        label = pt.widgets.Label("Your %s-%s semester courses" % (cur["year"], cur["semester"]))
        radioList = pt.widgets.RadioList(courses) if courses else pt.widgets.Label("(No courses)")
        actions = pt.layout.HSplit([
            pt.widgets.Button("Transcript", lambda: handler("transcript")),
            pt.widgets.Button("Enroll", lambda: handler("enroll")),
            pt.widgets.Button("Withdraw", lambda: handler("withdraw")),
            pt.widgets.Button("Personal Details", lambda: handler("profile"), width=20),
            pt.widgets.Button("Log out", lambda: handler("logout")),
        ])

        layout = pt.layout.VSplit([
            pt.layout.HSplit([
                label,
                radioList,
            ], padding=1),
            actions,
        ], padding=1)

        dialog = pt.shortcuts.dialogs.Dialog(
            title="Welcome, %s. Today is %s-%s-%s" % (profile["username"], cur["year"], cur["month"], cur["day"]),
            body=layout,
            with_background=True)

        answer = pt.shortcuts.dialogs._run_dialog(dialog, None)

        if answer == "transcript":
            showTranscript()
        elif answer == "enroll":
            showEnrollment()
        elif answer == "profile":
            showProfile()
        elif answer == "withdraw":
            showWithdraw()
        else: # user pressed logout
            return

def showTranscript():
    while True:
        cursor = connection.cursor()
        cursor.execute("select uosCode, semester, year, grade from transcript where studId = %s", (profile["id"], ))
        values = cursor.fetchall()
        cursor.close()

        values.sort(key=lambda v: (v[2], v[1]), reverse=True) # sort by year, semester descending
        courses = list(map(lambda v: ( 
            v[0],
            "   ".join([
                v[0], # course id
                v[1], # semester
                str(v[2]), # year
                str(v[3] or "N/A"), # grade
            ]),
        ), values))

        answer = pt.shortcuts.radiolist_dialog(
            title="%s's transcript" % profile["username"],
            text="Select course to see details",
            ok_text="See detail",
            cancel_text="Return",
            values=courses
        ) if courses else pt.shortcuts.message_dialog(
            title="%s's transcript" % profile["username"],
            text="(No courses)",
            ok_text="Return",
        )
        if answer == None: # user pressed return
            return
        else:
            showCourseDetail(answer)

def showCourseDetail(courseId: str):
    # print(courseId)
    cursor = connection.cursor()
    cursor.execute("""
        select uosName
        from unitofstudy
        where uosCode = %s
    """, (courseId, ))
    courseName, = cursor.fetchall()[0]

    cursor.execute("""
        select semester, year, grade
        from transcript
        where studId = %s and uosCode = %s
    """, (profile["id"], courseId))
    semester, year, grade = cursor.fetchall()[0]

    cursor.execute("""
        select uosoffering.enrollment, uosoffering.maxEnrollment, faculty.name
        from uosoffering, faculty
        where uosoffering.uosCode = %s and uosoffering.semester = %s and uosoffering.year = %s and uosoffering.instructorId = faculty.id
    """, (courseId, semester, year))
    enrollment, maxEnrollment, instructorName = cursor.fetchall()[0]

    cursor.close()

    answer = pt.shortcuts.message_dialog(
        title="%s: %s" % (courseId, courseName),
        text=pt.HTML("""
            <b>course id</b> %s \n
            <b>course name</b> %s \n
            <b>year</b> %d \n
            <b>semester</b> %s \n
            <b>enrollment</b> %d \n
            <b>max enrollment</b> %d \n
            <b>instructor name</b> %s \n
            <b>grade</b> %s
        """ % (courseId, courseName, year, semester, enrollment, maxEnrollment, instructorName, grade or "N/A"))
    )
    return

def showEnrollment():
    if cur['semester'] == "Q2":
        nextYear = cur['year'] + 1
        nextSemester = "Q1"
    elif cur['semester'] == "Q1":
        nextYear = cur['year']
        nextSemester = "Q2"

    while True:
        cursor = connection.cursor()
        cursor.execute("""
            select distinct uosCode, semester, year, classTime, classroomId
            from lecture
            where (year = %s and semester = %s)
            or (year = %s and semester = %s)
            order by year, semester ASC
        """, (cur['year'], cur['semester'], nextYear, nextSemester))
        # Students shall be able to select a specific course offering in this screen, but only subject offerings of the current year and quarter or the following quarter shall be presented.
        values = cursor.fetchall()
        cursor.close()

        courseTimeLocationMapping = {}

        for v in values:
            course = (v[0], v[1], str(v[2]))
            classTime = v[3]
            classroomId = v[4]

            if course in courseTimeLocationMapping:
                courseTimeLocationMapping[course].append((classTime, classroomId))
            else:
                courseTimeLocationMapping[course] = [(classTime, classroomId)]

        keys = sorted(courseTimeLocationMapping.keys(), key=lambda k: (k[2], k[1]), reverse=True)
        courses = list((k, "    ".join(k) + "   " + ", ".join(time + " @ " + id for time, id in courseTimeLocationMapping[k])) for k in keys)

        answer = pt.shortcuts.radiolist_dialog(
            title="%s-%s and %s-%s Courses" % (cur['year'], cur['semester'], nextYear, nextSemester),
            text="Courses available for this and next semester are listed",
            ok_text="Select",
            cancel_text="Return",
            values=courses,
        ) if courses else pt.shortcuts.message_dialog(
            title="%s-%s and %s-%s Courses" % (cur['year'], cur['semester'], nextYear, nextSemester),
            text="(No courses available at this time)",
            ok_text="Return",
        )
        if answer == None: # user pressed return
            return
        else:
            courseId, semester, year = answer
            confirm = pt.shortcuts.yes_no_dialog(
                title='Confirm Enrollment',
                text='Do you want to select %s for %s %s?' % (courseId, semester, year),
            )

            if confirm: # user pressed yes
                p_out = 0
                cursor = connection.cursor()

                cursor.execute("""
                drop procedure if exists check_enroll
                """)
                cursor.execute("""
                create procedure check_enroll(out p_out int, in lec_code char(8), in stu_id int, in year_in int, in semester_in char(2))
                begin
                declare req_cnt decimal default 0;
                declare pre_cnt decimal default 0;
                declare enroll decimal default 0;
                declare max_en decimal default 0;

                select count(requires.prerequoscode)
                into req_cnt
                from requires
                where requires.uoscode = lec_code;

                select count(transcript.uoscode)
                into pre_cnt
                from transcript, requires
                where requires.uoscode = lec_code
                and studID = stu_id
                and requires.prerequoscode = transcript.uoscode
                and transcript.grade is not null;

                select enrollment, maxenrollment
                into enroll, max_en
                from uosoffering
                where uoscode = lec_code
                and year = year_in
                and semester = semester_in;

                if exists(
                    select *
                    from transcript
                    where studID = stu_id
                    and uoscode = lec_code
                )
                then
                    set p_out = 1;
                elseif (req_cnt > pre_cnt)
                then
                    set p_out = 2;
                elseif (enroll >= max_en)
                then
                    set p_out = 3;
                else
                    set p_out = 4;

                    start transaction;

                    insert into transcript
                    values(stu_id, lec_code, semester_in, year_in, null);

                    update uosoffering
                    set enrollment = enrollment + 1
                    where uoscode = lec_code
                    and year = year_in
                    and semester = semester_in;

                    commit;
                end if;
                select @p_out;
                end""")
                # On successful enrollment, a new entry in the Transcript table shall be created with a NULL grade, plus the Enrollment attribute of the corresponding course shall be increased by one.
                # All database modifications (such as course enrolling / withdrawing or student update) shall be implemented as well-defined database transactions.

                args = (p_out, courseId, profile['id'], year, semester)
                args = cursor.callproc('check_enroll', args)
                # Implement this part using stored procedures and call it from your database client program.
                connection.commit()
                cursor.close()

                p_out = args[0]

                # Judge duplicate
                if p_out == 1:
                    pt.shortcuts.message_dialog(
                        title="Lecture Selection Failed",
                        text="Cannot select duplicate lectures!",
                        style=pt.styles.Style.from_dict({
                            "dialog": "bg:#ff0000",
                        }),
                    )
                    continue

                # Judge prerequisite
                elif p_out == 2:
                    cursor = connection.cursor()
                    cursor.execute("""
                        select requires.prerequoscode
                        from requires
                        where requires.uoscode = %s
                    """, (courseId, ))
                    req = cursor.fetchall()
                    cursor.close()

                    prerequisites = ", ".join(v[0] for v in req)

                    pt.shortcuts.message_dialog(
                        title="Lecture Selection Failed",
                        text="To select %s, you should complete %s first!" % (courseId, prerequisites),
                        style=pt.styles.Style.from_dict({
                            "dialog": "bg:#ff0000",
                        }),
                    )
                    # In case the student cannot enroll because he/she has not cleared the prerequisites, print those prerequisites on the screen.
                    continue

                # Judge max enrollment
                elif p_out == 3:
                    cursor = connection.cursor()
                    cursor.execute("""
                        select enrollment, maxenrollment
                        from uosoffering
                        where uoscode = %s
                        and year = %s
                        and semester = %s
                    """,  (courseId, year, semester))
                    judge3 = cursor.fetchall()
                    cursor.close()

                    pt.shortcuts.message_dialog(
                        title="Lecture Selection Failed",
                        text="%s is full now(%s/%s)!" % (courseId, judge3[0][0], judge3[0][1]),
                        style=pt.styles.Style.from_dict({
                            "dialog": "bg:#ff0000",
                        }),
                    )
                    continue

                # All cases passed, now update information
                elif p_out == 4:
                    pt.shortcuts.message_dialog(
                        title="Lecture Selection Succeed",
                        text="Congratulations! You have selected %s for %s %s successfully!" % (courseId, semester, year),
                        style=pt.styles.Style.from_dict({
                            "dialog": "bg:#00ff00",
                        }),
                    )
                    continue
                else:
                    raise ValueError("Wrong P_OUT!")

def showWithdraw():
    while True:
        if cur['semester'] == "Q2":
            nextYear = cur['year'] + 1
            nextSemester = "Q1"
        elif cur['semester'] == "Q1":
            nextYear = cur['year']
            nextSemester = "Q2"

        cursor = connection.cursor()
        cursor.execute("""
            select distinct uosCode, semester, year, grade
            from transcript
            where
                studId = %s
                and (
                    (year = %s and semester = %s)
                    or (year = %s and semester = %s)
                )
        """, (profile["id"], cur['year'], cur['semester'], nextYear, nextSemester))
        # Students can only withdraw from a unit that they have not finished so far (i.e. grade is NULL).
        # TA says students can only withdraw from unfinished (this semester or next semesters) courses
        values = cursor.fetchall()
        cursor.close()

        courses = list(map(lambda v: (
            (v[0], v[1], str(v[2])), # course id, semester, year
            "   ".join([
                v[0], # course id
                v[1], # semester
                str(v[2]), # year
                str(v[3] or "N/A"), # grade
            ]),
        ), values))

        answer = pt.shortcuts.radiolist_dialog(
            title="Withdraw Lecture",
            text="You can only withdraw unfinished courses for this semester or next semester.",
            ok_text="Withdraw",
            cancel_text="Return",
            values=courses
        ) if courses else pt.shortcuts.message_dialog(
            title="Withdraw Lecture",
            text="You can only withdraw unfinished courses for this semester or next semester.\n\n(No courses to withdraw)",
            ok_text="Return",
        )

        if answer == None: # user pressed return
            return
        else:
            courseId, semester, year = answer

            confirm = pt.shortcuts.yes_no_dialog(
                title='Confirm',
                text='Do you want to withdraw %s (%s %s)?' % (courseId, semester, year),
            )

            if confirm:
                # judge if graded
                cursor = connection.cursor()
                cursor.execute("""
                    select distinct uosCode, semester, year, grade
                    from transcript
                    where studId = %s and year = %s
                    and semester = %s and uosCode = %s
                """, (profile["id"], year, semester, courseId))
                temp_grade = cursor.fetchall()[0][-1]
                cursor.close()
                if temp_grade != None:
                    pt.shortcuts.message_dialog(
                        title="Lecture Withdraw Failed",
                        text="You can not drop a class already graded!",
                        style=pt.styles.Style.from_dict({
                            "dialog": "bg:#ff0000",
                        }),
                    )
                    continue

                p_out = 0
                cursor = connection.cursor()
                #trigger
                cursor.execute("""
                drop trigger if exists check_halfenroll""")
                cursor.execute("""
                create trigger check_halfenroll
                after update on uosoffering
                for each row
                if new.enrollment < old.enrollment
                then
                if (select enrollment from uosoffering
                where UoSCode = new.UoSCode and year = new.year
                and semester = new.Semester) <
                (select MaxEnrollment/2 from uosoffering
                where UoSCode = new.UoSCode and year = new.year
                and semester = new.Semester) then
                begin
                    insert into whenoffered
                    values('test', 'T');
                end;
                else
                    insert into whenoffered
                    values('test', 'NT');
                end if;
                end if""")
                cursor.execute("""
                drop procedure if exists check_withdraw""")
                cursor.execute("""
                create procedure check_withdraw(in lec_code char(8), in stu_id int, in year_in int, in semester_in char(2), out trigger_val char(8))
                begin
                    start transaction;

                    delete from transcript
                    where StudId = stu_id and UoSCode = lec_code
                    and Semester = semester_in and year = year_in;

                    update uosoffering
                    set enrollment = enrollment - 1
                    where uoscode = lec_code
                    and year = year_in
                    and semester = semester_in;

                    select semester
                    into trigger_val
                    from whenoffered
                    where uoscode = 'test';

                    delete from whenoffered
                    where uoscode = 'test';

                    commit;
                end""")
                # Implement this part using stored procedures and call it from your database client program.
                # All database modifications (such as course enrolling / withdrawing or student update) shall be implemented as well-defined database transactions.
                args = (courseId, profile['id'], year, semester, p_out)
                args = cursor.callproc('check_withdraw', args)
                connection.commit()
                cursor.close()

                if args[-1] == 'T':
                    pt.shortcuts.message_dialog(
                        title="Lecture Withdraw Warning",
                        text="Lecture %s (%s %s) now contains less than half MaxEnrollment!" % (courseId, semester, year),
                        style=pt.styles.Style.from_dict({
                            "dialog": "bg:#ffff00",
                        }),
                    )
                    # If the Enrollment number goes below 50% of the MaxEnrollment, then a warning message should be shown on the screen.

                pt.shortcuts.message_dialog(
                    title="Lecture Withdraw Succeed",
                    text="Congratulations! You have withdrawn from %s (%s %s) successfully!" % (courseId, semester, year),
                    style=pt.styles.Style.from_dict({
                        "dialog": "bg:#00ff00",
                    }),
                )

# personal details
def showProfile():
    while True:
        profile.update(getProfile(profile["id"])) # get latest profile
        text = pt.HTML("""
            <b>student id</b> %s \n
            <b>name</b> %s \n
            <b>address</b> %s \n
            <b>password</b> %s \n
        """ % (profile["id"], profile["username"], profile["address"], profile["password"]))
        actions = pt.layout.HSplit([
            pt.widgets.Button("Change  address", lambda: handler("address"), 20),
            pt.widgets.Button("Change password", lambda: handler("password"), 20),
            pt.widgets.Button("Return", lambda: handler("return")),
        ])
        layout = pt.layout.VSplit([
            pt.widgets.Label(text),
            actions,
        ], padding=1)
        dialog = pt.shortcuts.dialogs.Dialog(
            title="Personal Details",
            body=layout,
            with_background=True
        )
        answer = pt.shortcuts.dialogs._run_dialog(dialog, None)

        if answer == "address":
            newAddress = pt.shortcuts.input_dialog(
                title="Change Address",
                text="New address",
                cancel_text='Cancel',
            )
            if newAddress == None: # user pressed cancel
                pass # do nothing
            else:
                cursor = connection.cursor() # implicit transaction, defined by PEP 249. See <https://www.python.org/dev/peps/pep-0249/#commit> and <https://stackoverflow.com/questions/52723251/mysql-connector-python-how-to-use-the-start-transaction-method>
                cursor.execute("""
                    update student
                    set address = %s
                    where id = %s
                """, (newAddress, profile["id"]))
                connection.commit() # commit transaction
                cursor.close()
        elif answer == "password":
            newPassword = pt.shortcuts.input_dialog(
                title="Change Password",
                text="New password",
                cancel_text='Cancel',
            )
            if newPassword == None: # user pressed cancel
                pass # do nothing
            else:
                if newPassword == "": # password is empty
                    pt.shortcuts.message_dialog(
                        title="New Password Failed",
                        text="Password should not be empty!",
                        style=pt.styles.Style.from_dict({"dialog": "bg:#ff0000"}),
                    ) # give a warning
                else: # password is not empty
                    cursor = connection.cursor()
                    cursor.execute("""
                        update student
                        set password = %s
                        where id = %s
                    """, (newPassword, profile["id"]))
                    connection.commit() # commit transaction
                    cursor.close()
        else: # user pressed return
            return

if __name__ == "__main__":
    try:
        connection = mysql.connector.connect(user="root", password="19961226syc", database="project3-nudb", host="localhost", port=3306)
        main()
    except:
        traceback.print_exc()
    finally:
        connection.close()
