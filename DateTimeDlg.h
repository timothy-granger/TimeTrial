#ifndef DATETIMEDLG_H
#define DATETIMEDLG_H

#include <QDialog>
#include <QDateTime>

namespace Ui {
class DateTimeDlg;
}

class DateTimeDlg : public QDialog
{
    Q_OBJECT

public:
    explicit DateTimeDlg(QWidget *parent = 0);
    ~DateTimeDlg();

    void        setLabel          ( QString   sLabel   );
    void        setDateTime       ( QDateTime qVal     );
    void        setMinimumDateTime( QDateTime qMin     );
    void        setMaximumDateTime( QDateTime qMax     );

    QDateTime   dateTime( void );

private:
    Ui::DateTimeDlg *ui;
};

#endif // DATETIMEDLG_H
