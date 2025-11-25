from flask import Flask, render_template, request, redirect, session, flash, jsonify
import os
from datetime import timedelta  # used for setting session timeout
import pandas as pd
import plotly
import plotly.express as px
import json
import warnings
import support

warnings.filterwarnings("ignore")

app = Flask(__name__)
app.secret_key = os.urandom(24)

# Add currency config + Jinja filter for Philippine Peso
app.config['CURRENCY_SYMBOL'] = '₱'


def format_currency(value):
    try:
        n = float(value)
    except (TypeError, ValueError):
        return value
    sign = '-' if n < 0 else ''
    n = abs(n)
    # e.g. ₱1,234.56
    return f"{sign}{app.config['CURRENCY_SYMBOL']}{n:,.2f}"


app.jinja_env.filters['currency'] = format_currency


@app.route('/')
def login():
    session.permanent = True
    app.permanent_session_lifetime = timedelta(minutes=15)
    if 'user_id' in session:  # if logged-in
        flash("Already a user is logged-in!")
        return redirect('/home')
    else:  # if not logged-in
        return render_template("login.html")


@app.route('/login_validation', methods=['POST'])
def login_validation():
    if 'user_id' not in session:  # if user not logged-in
        email = request.form.get('email')
        passwd = request.form.get('password')
        query = """SELECT * FROM user_login WHERE email LIKE '{}' AND password LIKE '{}'""".format(email, passwd)
        users = support.execute_query("search", query)
        if len(users) > 0:  # if user details matched in db
            session['user_id'] = users[0][0]
            return redirect('/home')
        else:  # if user details not matched in db
            flash("Invalid email and password!")
            return redirect('/')
    else:  # if user already logged-in
        flash("Already a user is logged-in!")
        return redirect('/home')


@app.route('/reset', methods=['POST'])
def reset():
    if 'user_id' not in session:
        email = request.form.get('femail')
        pswd = request.form.get('pswd')
        userdata = support.execute_query('search', """select * from user_login where email LIKE '{}'""".format(email))
        if len(userdata) > 0:
            try:
                query = """update user_login set password = '{}' where email = '{}'""".format(pswd, email)
                support.execute_query('insert', query)
                flash("Password has been changed!!")
                return redirect('/')
            except:
                flash("Something went wrong!!")
                return redirect('/')
        else:
            flash("Invalid email address!!")
            return redirect('/')
    else:
        return redirect('/home')


@app.route('/register')
def register():
    if 'user_id' in session:  # if user is logged-in
        flash("Already a user is logged-in!")
        return redirect('/home')
    else:  # if not logged-in
        return render_template("register.html")


@app.route('/registration', methods=['POST'])
def registration():
    if 'user_id' not in session:  # if not logged-in
        name = request.form.get('name')
        email = request.form.get('email')
        passwd = request.form.get('password')
        if len(name) > 5 and len(email) > 10 and len(passwd) > 5:  # if input details satisfy length condition
            try:
                query = """INSERT INTO user_login(username, email, password) VALUES('{}','{}','{}')""".format(name,
                                                                                                              email,
                                                                                                              passwd)
                support.execute_query('insert', query)

                user = support.execute_query('search',
                                             """SELECT * from user_login where email LIKE '{}'""".format(email))
                session['user_id'] = user[0][0]  # set session on successful registration
                flash("Successfully Registered!!")
                return redirect('/home')
            except:
                flash("Email id already exists, use another email!!")
                return redirect('/register')
        else:  # if input condition length not satisfy
            flash("Not enough data to register, try again!!")
            return redirect('/register')
    else:  # if already logged-in
        flash("Already a user is logged-in!")
        return redirect('/home')


@app.route('/contact')
def contact():
    return render_template("contact.html")


@app.route('/feedback', methods=['POST'])
def feedback():
    name = request.form.get("name")
    email = request.form.get("email")
    phone = request.form.get("phone")
    sub = request.form.get("sub")
    message = request.form.get("message")
    flash("Thanks for reaching out to us. We will contact you soon.")
    return redirect('/')


@app.route('/home')
def home():
    if 'user_id' in session:  # if user is logged-in
        query = """select * from user_login where user_id = {} """.format(session['user_id'])
        userdata = support.execute_query("search", query)

        table_query = """select * from user_expenses where user_id = {} order by pdate desc limit 20""".format(
            session['user_id'])
        table_data = support.execute_query("search", table_query)
        df_query = """select * from user_expenses where user_id = {} order by pdate desc""".format(
            session['user_id'])
        df_data = support.execute_query("search", df_query)
        df = pd.DataFrame(df_data, columns=['#', 'User_Id', 'Date', 'Expense', 'Amount', 'Note'])

        df = support.generate_df(df)
        try:
            earning, spend, invest, saving = support.top_tiles(df)
        except:
            earning, spend, invest, saving = 0, 0, 0, 0

        try:
            bar, pie, line, stack_bar = support.generate_Graph(df)
        except:
            bar, pie, line, stack_bar = None, None, None, None
        try:
            monthly_data = support.get_monthly_data(df, res=None)
        except:
            monthly_data = []
        try:
            card_data = support.sort_summary(df)
        except:
            card_data = []

        try:
            goals = support.expense_goal(df)
        except:
            goals = []
        try:
            size = 240
            pie1 = support.makePieChart(df, 'Earning', 'Month_name', size=size)
            pie2 = support.makePieChart(df, 'Spend', 'Day_name', size=size)
            pie3 = support.makePieChart(df, 'Investment', 'Year', size=size)
            pie4 = support.makePieChart(df, 'Saving', 'Note', size=size)
            pie5 = support.makePieChart(df, 'Saving', 'Day_name', size=size)
            pie6 = support.makePieChart(df, 'Investment', 'Note', size=size)
        except:
            pie1, pie2, pie3, pie4, pie5, pie6 = None, None, None, None, None, None
        return render_template('home.html',
                               user_name=userdata[0][1],
                               df_size=df.shape[0],
                               df=jsonify(df.to_json()),
                               earning=earning,
                               spend=spend,
                               invest=invest,
                               saving=saving,
                               monthly_data=monthly_data,
                               card_data=card_data,
                               goals=goals,
                               table_data=table_data,
                               bar=bar,
                               line=line,
                               stack_bar=stack_bar,
                               pie1=pie1,
                               pie2=pie2,
                               pie3=pie3,
                               pie4=pie4,
                               pie5=pie5,
                               pie6=pie6,
                               )
    else:  # if not logged-in
        return redirect('/')


@app.route('/home/add_expense', methods=['POST'])
def add_expense():
    if 'user_id' in session:
        user_id = session['user_id']
        if request.method == 'POST':
            date = request.form.get('e_date')
            expense = request.form.get('e_type')
            amount = request.form.get('amount')
            notes = request.form.get('notes')
            try:
                query = """insert into user_expenses (user_id, pdate, expense, amount, pdescription) values 
                ({}, '{}','{}',{},'{}')""".format(user_id, date, expense, amount, notes)
                support.execute_query('insert', query)
                flash("Saved!!")
            except:
                flash("Something went wrong.")
                return redirect("/home")
            return redirect('/home')
    else:
        return redirect('/')


@app.route('/home/filter_records', methods=['POST'])
def filter_records():
    if 'user_id' in session:
        try:
            data = request.get_json()
            start_date = data.get('start_date', '')
            end_date = data.get('end_date', '')
            category = data.get('category', '')
            min_amount = data.get('min_amount', '')
            max_amount = data.get('max_amount', '')
            keyword = data.get('keyword', '')
            
            # Build dynamic query
            query = """SELECT * FROM user_expenses WHERE user_id = {}""".format(session['user_id'])
            
            if start_date:
                query += """ AND pdate >= '{}'""".format(start_date)
            if end_date:
                query += """ AND pdate <= '{}'""".format(end_date)
            if category:
                query += """ AND expense = '{}'""".format(category)
            if min_amount:
                query += """ AND amount >= {}""".format(float(min_amount))
            if max_amount:
                query += """ AND amount <= {}""".format(float(max_amount))
            if keyword:
                query += """ AND (pdescription LIKE '%{}%' OR expense LIKE '%{}%')""".format(keyword, keyword)
            
            query += """ ORDER BY pdate DESC"""
            
            filtered_data = support.execute_query("search", query)
            
            return jsonify({
                'records': filtered_data,
                'count': len(filtered_data)
            })
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    else:
        return jsonify({'error': 'Unauthorized'}), 401


@app.route('/home/edit_expense', methods=['POST'])
def edit_expense():
    if 'user_id' in session:
        try:
            data = request.get_json()
            record_id = data.get('id')
            date = data.get('date')
            expense = data.get('expense')
            amount = data.get('amount')
            note = data.get('note')
            
            # Verify the record belongs to the logged-in user
            verify_query = """SELECT * FROM user_expenses WHERE id = {} AND user_id = {}""".format(
                record_id, session['user_id'])
            existing_record = support.execute_query('search', verify_query)
            
            if len(existing_record) == 0:
                return jsonify({'error': 'Record not found or unauthorized'}), 403
            
            # Update the record
            update_query = """UPDATE user_expenses SET pdate = '{}', expense = '{}', amount = {}, pdescription = '{}' 
                           WHERE id = {} AND user_id = {}""".format(
                date, expense, float(amount), note, record_id, session['user_id'])
            support.execute_query('insert', update_query)
            
            return jsonify({'success': True, 'message': 'Record updated successfully'})
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    else:
        return jsonify({'error': 'Unauthorized'}), 401


@app.route('/home/delete_expense', methods=['POST'])
def delete_expense():
    if 'user_id' in session:
        try:
            data = request.get_json()
            record_id = data.get('id')
            
            # Verify the record belongs to the logged-in user
            verify_query = """SELECT * FROM user_expenses WHERE id = {} AND user_id = {}""".format(
                record_id, session['user_id'])
            existing_record = support.execute_query('search', verify_query)
            
            if len(existing_record) == 0:
                return jsonify({'error': 'Record not found or unauthorized'}), 403
            
            # Delete the record
            delete_query = """DELETE FROM user_expenses WHERE id = {} AND user_id = {}""".format(
                record_id, session['user_id'])
            support.execute_query('insert', delete_query)
            
            return jsonify({'success': True, 'message': 'Record deleted successfully'})
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    else:
        return jsonify({'error': 'Unauthorized'}), 401


@app.route('/home/get_goals', methods=['GET'])
def get_goals():
    if 'user_id' in session:
        try:
            query = """SELECT id, goal_text, completed FROM user_goals WHERE user_id = {} ORDER BY created_at DESC""".format(
                session['user_id'])
            goals = support.execute_query('search', query)
            goals_list = [{'id': g[0], 'text': g[1], 'completed': bool(g[2])} for g in goals]
            return jsonify({'success': True, 'goals': goals_list})
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    else:
        return jsonify({'error': 'Unauthorized'}), 401


@app.route('/home/save_goal', methods=['POST'])
def save_goal():
    if 'user_id' in session:
        try:
            data = request.get_json()
            goal_text = data.get('text', '').strip()
            
            if not goal_text:
                return jsonify({'error': 'Goal text cannot be empty'}), 400
            
            query = """INSERT INTO user_goals (user_id, goal_text) VALUES ({}, '{}')""".format(
                session['user_id'], goal_text.replace("'", "''"))
            support.execute_query('insert', query)
            
            return jsonify({'success': True, 'message': 'Goal saved successfully'})
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    else:
        return jsonify({'error': 'Unauthorized'}), 401


@app.route('/home/toggle_goal', methods=['POST'])
def toggle_goal():
    if 'user_id' in session:
        try:
            data = request.get_json()
            goal_id = data.get('id')
            completed = data.get('completed', False)
            
            # Verify the goal belongs to the user
            verify_query = """SELECT * FROM user_goals WHERE id = {} AND user_id = {}""".format(
                goal_id, session['user_id'])
            existing = support.execute_query('search', verify_query)
            
            if len(existing) == 0:
                return jsonify({'error': 'Goal not found or unauthorized'}), 403
            
            update_query = """UPDATE user_goals SET completed = {} WHERE id = {} AND user_id = {}""".format(
                1 if completed else 0, goal_id, session['user_id'])
            support.execute_query('insert', update_query)
            
            return jsonify({'success': True, 'message': 'Goal updated successfully'})
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    else:
        return jsonify({'error': 'Unauthorized'}), 401


@app.route('/home/delete_goal', methods=['POST'])
def delete_goal():
    if 'user_id' in session:
        try:
            data = request.get_json()
            goal_id = data.get('id')
            
            # Verify the goal belongs to the user
            verify_query = """SELECT * FROM user_goals WHERE id = {} AND user_id = {}""".format(
                goal_id, session['user_id'])
            existing = support.execute_query('search', verify_query)
            
            if len(existing) == 0:
                return jsonify({'error': 'Goal not found or unauthorized'}), 403
            
            delete_query = """DELETE FROM user_goals WHERE id = {} AND user_id = {}""".format(
                goal_id, session['user_id'])
            support.execute_query('insert', delete_query)
            
            return jsonify({'success': True, 'message': 'Goal deleted successfully'})
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    else:
        return jsonify({'error': 'Unauthorized'}), 401


@app.route('/home/get_savings_goal', methods=['GET'])
def get_savings_goal():
    if 'user_id' in session:
        try:
            query = """SELECT id, goal_name, target_amount, current_amount FROM user_savings_tracker 
                      WHERE user_id = {} ORDER BY created_at DESC LIMIT 1""".format(session['user_id'])
            result = support.execute_query('search', query)
            
            if len(result) > 0:
                savings_data = {
                    'id': result[0][0],
                    'goalName': result[0][1],
                    'targetAmount': result[0][2],
                    'currentAmount': result[0][3]
                }
                return jsonify({'success': True, 'savingsGoal': savings_data})
            else:
                return jsonify({'success': True, 'savingsGoal': None})
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    else:
        return jsonify({'error': 'Unauthorized'}), 401


@app.route('/home/save_savings_goal', methods=['POST'])
def save_savings_goal():
    if 'user_id' in session:
        try:
            data = request.get_json()
            goal_name = data.get('goalName', '').strip()
            target_amount = float(data.get('targetAmount', 0))
            current_amount = float(data.get('currentAmount', 0))
            
            if not goal_name or target_amount <= 0:
                return jsonify({'error': 'Invalid goal name or target amount'}), 400
            
            # Check if user already has a savings goal
            check_query = """SELECT id FROM user_savings_tracker WHERE user_id = {}""".format(session['user_id'])
            existing = support.execute_query('search', check_query)
            
            if len(existing) > 0:
                # Update existing goal
                update_query = """UPDATE user_savings_tracker SET goal_name = '{}', target_amount = {}, 
                                 current_amount = {}, updated_at = CURRENT_TIMESTAMP 
                                 WHERE user_id = {}""".format(
                    goal_name.replace("'", "''"), target_amount, current_amount, session['user_id'])
                support.execute_query('insert', update_query)
            else:
                # Create new goal
                insert_query = """INSERT INTO user_savings_tracker (user_id, goal_name, target_amount, current_amount) 
                                 VALUES ({}, '{}', {}, {})""".format(
                    session['user_id'], goal_name.replace("'", "''"), target_amount, current_amount)
                support.execute_query('insert', insert_query)
            
            return jsonify({'success': True, 'message': 'Savings goal saved successfully'})
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    else:
        return jsonify({'error': 'Unauthorized'}), 401


@app.route('/home/update_savings', methods=['POST'])
def update_savings():
    if 'user_id' in session:
        try:
            data = request.get_json()
            amount = float(data.get('amount', 0))
            
            # Get current savings goal
            query = """SELECT id, current_amount FROM user_savings_tracker WHERE user_id = {} 
                      ORDER BY created_at DESC LIMIT 1""".format(session['user_id'])
            result = support.execute_query('search', query)
            
            if len(result) == 0:
                return jsonify({'error': 'No savings goal found'}), 404
            
            new_amount = result[0][1] + amount
            
            update_query = """UPDATE user_savings_tracker SET current_amount = {}, 
                             updated_at = CURRENT_TIMESTAMP WHERE id = {} AND user_id = {}""".format(
                new_amount, result[0][0], session['user_id'])
            support.execute_query('insert', update_query)
            
            return jsonify({'success': True, 'message': 'Savings updated successfully', 'newAmount': new_amount})
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    else:
        return jsonify({'error': 'Unauthorized'}), 401


@app.route('/analysis')
def analysis():
    if 'user_id' in session:  # if already logged-in
        query = """select * from user_login where user_id = {} """.format(session['user_id'])
        userdata = support.execute_query('search', query)
        query2 = """select pdate,expense, pdescription, amount from user_expenses where user_id = {}""".format(
            session['user_id'])

        data = support.execute_query('search', query2)
        df = pd.DataFrame(data, columns=['Date', 'Expense', 'Note', 'Amount(₱)'])
        df = support.generate_df(df)

        if df.shape[0] > 0:
            pie = support.meraPie(df=df, names='Expense', values='Amount(₱)', hole=0.7, hole_text='Expense',
                                  hole_font=20,
                                  height=180, width=180, margin=dict(t=1, b=1, l=1, r=1))
            df2 = df.groupby(['Note', "Expense"]).sum().reset_index()[["Expense", 'Note', 'Amount(₱)']]
            bar = support.meraBarChart(df=df2, x='Note', y='Amount(₱)', color="Expense", height=180, x_label="Category",
                                       show_xtick=False)
            line = support.meraLine(df=df, x='Date', y='Amount(₱)', color='Expense', slider=False, show_legend=False,
                                    height=180)
            scatter = support.meraScatter(df, 'Date', 'Amount(₱)', 'Expense', 'Amount(₱)', slider=False, )
            heat = support.meraHeatmap(df, 'Day_name', 'Month_name', height=200, title="Transaction count Day vs Month")
            month_bar = support.month_bar(df, 280)
            sun = support.meraSunburst(df, 280)

            return render_template('analysis.html',
                                   user_name=userdata[0][1],
                                   pie=pie,
                                   bar=bar,
                                   line=line,
                                   scatter=scatter,
                                   heat=heat,
                                   month_bar=month_bar,
                                   sun=sun
                                   )
        else:
            flash("No data records to analyze.")
            return redirect('/home')

    else:  # if not logged-in
        return redirect('/')


@app.route('/profile')
def profile():
    if 'user_id' in session:  # if logged-in
        query = """select * from user_login where user_id = {} """.format(session['user_id'])
        userdata = support.execute_query('search', query)
        return render_template('profile.html', user_name=userdata[0][1], email=userdata[0][2])
    else:  # if not logged-in
        return redirect('/')


@app.route("/updateprofile", methods=['POST'])
def update_profile():
    name = request.form.get('name')
    email = request.form.get("email")
    query = """select * from user_login where user_id = {} """.format(session['user_id'])
    userdata = support.execute_query('search', query)
    query = """select * from user_login where email = "{}" """.format(email)
    email_list = support.execute_query('search', query)
    if name != userdata[0][1] and email != userdata[0][2] and len(email_list) == 0:
        query = """update user_login set username = '{}', email = '{}' where user_id = '{}'""".format(name, email,
                                                                                                      session[
                                                                                                          'user_id'])
        support.execute_query('insert', query)
        flash("Name and Email updated!!")
        return redirect('/profile')
    elif name != userdata[0][1] and email != userdata[0][2] and len(email_list) > 0:
        flash("Email already exists, try another!!")
        return redirect('/profile')
    elif name == userdata[0][1] and email != userdata[0][2] and len(email_list) == 0:
        query = """update user_login set email = '{}' where user_id = '{}'""".format(email, session['user_id'])
        support.execute_query('insert', query)
        flash("Email updated!!")
        return redirect('/profile')
    elif name == userdata[0][1] and email != userdata[0][2] and len(email_list) > 0:
        flash("Email already exists, try another!!")
        return redirect('/profile')

    elif name != userdata[0][1] and email == userdata[0][2]:
        query = """update user_login set username = '{}' where user_id = '{}'""".format(name, session['user_id'])
        support.execute_query('insert', query)
        flash("Name updated!!")
        return redirect("/profile")
    else:
        flash("No Change!!")
        return redirect("/profile")


@app.route('/logout')
def logout():
    try:
        session.pop("user_id")  # delete the user_id in session (deleting session)
        return redirect('/')
    except:  # if already logged-out but in another tab still logged-in
        return redirect('/')


if __name__ == "__main__":
    app.run(debug=True)
